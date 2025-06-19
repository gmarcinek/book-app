"""
ner/extractor/base.py

Enhanced Entity Extractor with batch per-chunk clustering
Clean implementation - delegating clustering to EntityBatchClusterer
"""

from datetime import datetime
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

# Local imports
from ..utils import log_memory_usage
from ..semantic import TextChunk
from ..semantic.config import get_default_semantic_config
from ..domains import DomainFactory
from ..config import NERConfig, create_default_ner_config
from ..storage import SemanticStore
from llm import Models, LLMConfig
from .entity_linker import EntityLinker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
   """Represents an extracted entity"""
   name: str
   type: str
   description: str
   confidence: float
   aliases: List[str] = None
   chunk_id: Optional[int] = None
   context: Optional[str] = None
   domain: Optional[str] = None
   evidence: Optional[str] = None
   
   def __post_init__(self):
       """Initialize aliases as empty list if None"""
       if self.aliases is None:
           self.aliases = []


class EntityExtractor:
    """Enhanced multi-domain entity extractor with batch clustering"""
   
    def __init__(self, 
                model: str = Models.QWEN_CODER, 
                config: Optional[NERConfig] = None,
                domain_names: List[str] = None,
                storage_dir: str = "semantic_store",
                enable_semantic_store: bool = True):
       
        self.config = config if config is not None else create_default_ner_config()
        self.semantic_config = get_default_semantic_config()
        self.model = model
        self.llm_client = None
        self.enable_semantic_store = enable_semantic_store
        
        # DEBUG
        self.llm_debug_dir = Path(f"llm_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.llm_debug_dir.mkdir(exist_ok=True)
        self.llm_call_counter = 0
        # DEBUG
        
        if domain_names is None:
            domain_names = ["literary", "liric"]
        
        self.domain_names = domain_names
       
        if domain_names == ["auto"]:
            self.domains = []
            logger.info("🤖 Initialized extractor with auto-classification mode")
        else:
            self.domains = DomainFactory.use(domain_names)
            logger.info(f"🔄 Initialized extractor with domains: 🗂️ {domain_names}")
       
        # Initialize SemanticStore
        if self.enable_semantic_store:
            try:
                self.semantic_store = SemanticStore(
                        storage_dir=storage_dir,
                        embedding_model="sentence-transformers/all-MiniLM-L6-v2"
                        # embedding_model="allegro/herbert-base-cased"
                )
                logger.info(f"🧠 SemanticStore enabled: {storage_dir}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize SemanticStore: {e}")
                self.semantic_store = None
                self.enable_semantic_store = False
        else:
            self.semantic_store = None
            logger.info("🚫 SemanticStore disabled")

        # Initialize EntityLinker
        self.entity_linker = EntityLinker(self.semantic_store)
        
        # Stats
        available_domains = ["literary", "liric", "simple", "owu"] if domain_names == ["auto"] else domain_names
       
        self.extraction_stats = {
            "chunks_processed": 0,
            "domains_used": len(self.domains) if self.domains else 0,
            "entities_extracted_raw": 0,
            "entities_extracted_valid": 0,
            "entities_rejected": 0,
            "failed_extractions": 0,
            "auto_classifications": 0,
            "auto_classification_failures": 0,
            "semantic_enhancements": 0,
            "semantic_deduplication_hits": 0,
            "by_domain": {name: {"raw": 0, "valid": 0, "rejected": 0} for name in available_domains}
        }
       
        self.context_stats = {
            'contexts_generated': 0,
            'entities_found_in_context': 0,
            'fallback_contexts_used': 0
        }
        
        self.meta_prompt_stats = {
            'meta_prompts_generated': 0,
            'meta_prompts_failed': 0,
            'fallback_to_standard_prompt': 0,
            'by_domain': {name: {"generated": 0, "failed": 0} for name in available_domains}
        }
   
    def _initialize_llm(self):
        """Initialize LLM client if needed"""
        if self.llm_client is None:
            try:
                from llm import LLMClient
                self.llm_client = LLMClient(self.model)
                logger.info(f"🤖 Initialized LLM model: {self.model}")
            except Exception as e:
                logger.error(f"💥 Failed to initialize LLM: {e}")
                raise
   
    def _call_llm_for_meta_analysis(self, prompt: str) -> str:
        """Call LLM for meta-analysis with dedicated config"""
        try:
            if self.llm_client is None:
                self._initialize_llm()
            
            config = LLMConfig(
                temperature=self.config.get_meta_analysis_temperature()
            )
            
            self._log_llm_call("meta_analysis", prompt, None)  # ← DODANE
            response = self.llm_client.chat(prompt, config)
            self._log_llm_call("meta_analysis", prompt, response)  # ← DODANE
            
            return response
            
        except Exception as e:
            logger.error(f"🔥 Meta-analysis LLM call failed: {e}")
            raise
   
    def _call_llm_for_entity_extraction(self, prompt: str) -> str:
        """Call LLM for entity extraction with dedicated config"""
        try:
            if self.llm_client is None:
                self._initialize_llm()
            
            config = LLMConfig(
                temperature=self.config.get_entity_extraction_temperature()
            )
            
            self._log_llm_call("entity_extraction", prompt, None)  # ← DODANE
            response = self.llm_client.chat(prompt, config)
            self._log_llm_call("entity_extraction", prompt, response)  # ← DODANE
            
            return response
            
        except Exception as e:
            logger.error(f"🔥 Entity extraction LLM call failed: {e}")
            raise
   
    def _call_llm_for_auto_classification(self, prompt: str) -> str:
        """Call LLM for auto-classification with dedicated config"""
        try:
            if self.llm_client is None:
                self._initialize_llm()
            
            config = LLMConfig(
                temperature=self.config.get_auto_classification_temperature()
            )
            
            self._log_llm_call("auto_classification", prompt, None)  # ← DODANE
            response = self.llm_client.chat(prompt, config)
            self._log_llm_call("auto_classification", prompt, response)  # ← DODANE
            
            return response
            
        except Exception as e:
            logger.error(f"🎯 Auto-classification LLM call failed: {e}")
            raise
    # DEBUG ------------------------------------------
    def _log_llm_call(self, call_type: str, prompt: str, response: str = None):
        """Log LLM call with timestamp"""
        self.llm_call_counter += 1
        timestamp = datetime.now().strftime("%H%M%S")
        
        if response is None:  # Request
            filename = f"{self.llm_call_counter:03d}_{timestamp}_{call_type}_REQUEST.txt"
            content = f"=== {call_type.upper()} REQUEST ===\n{prompt}"
        else:  # Response
            filename = f"{self.llm_call_counter:03d}_{timestamp}_{call_type}_RESPONSE.txt"
            content = f"=== {call_type.upper()} RESPONSE ===\n{response}"
        
        (self.llm_debug_dir / filename).write_text(content, encoding='utf-8')
    # DEBUG ------------------------------------------
    
    
    def extract_entities(self, chunks: List[TextChunk]) -> List[ExtractedEntity]:
        """BATCH entity extraction with batch clustering per chunk"""
        from .extraction import extract_entities_from_chunk_multi_domain
        from .deduplication import _deduplicate_entities
        from .batch_clustering import EntityBatchClusterer
        from .entity_linker import EntityLinker
        
        self._initialize_llm()
        
        all_entities = []
        chunk_ids_mapping = {}
        
        if self.domain_names == ["auto"]:
            logger.info(f"🔄 Starting batch auto-classification from {len(chunks)} chunks")
        else:
            logger.info(f"🔄 Starting batch multi-domain extraction from {len(chunks)} chunks")

        if hasattr(self, "aggregator") is False and hasattr(chunks[0], "aggregator"):
            self.aggregator = chunks[0].aggregator
        
        # PHASE 1: Register chunks
        if self.semantic_store:
            logger.info(f"📝 Registering {len(chunks)} chunks...")
            for chunk in chunks:
                chunk_data = {
                    'text': chunk.text,
                    'document_source': chunk.document_source,
                    'start_pos': chunk.start,
                    'end_pos': chunk.end,
                    'chunk_index': chunk.id
                }
                chunk_id = self.semantic_store.register_chunk(chunk_data)
                chunk_ids_mapping[chunk.id] = chunk_id
        
        # PHASE 2: Extract + BATCH cluster per chunk
        clusterer = EntityBatchClusterer(self.semantic_store, self.extraction_stats) if self.semantic_store else None
        
        for chunk in chunks:
            try:
                chunk_id = chunk_ids_mapping.get(chunk.id) if self.semantic_store else None
                
                # Extract entities (no clustering yet)
                entities, chunk_relationships = extract_entities_from_chunk_multi_domain(
                    self, chunk, self.domains, self.domain_names, chunk_id
                )

                # Resolve relationships names → IDs
                resolved_relationships = []
                for rel in chunk_relationships:
                    resolved = self.entity_linker.resolve_relationship(rel)
                    if resolved:
                        resolved_relationships.append(resolved)

                # Store relationships in SemanticStore
                if self.semantic_store and resolved_relationships:
                    for rel in resolved_relationships:
                        self.semantic_store.relationship_manager.add_structural_relationship(
                            rel['source_id'], rel['target_id'], rel['pattern'], 
                            rel['confidence'], evidence=rel['evidence']
                        )
                
                for entity in entities:
                    entity.chunk_id = chunk.id
                    if chunk_id:
                        entity.semantic_chunk_id = chunk_id
                
                # BATCH cluster entities from this chunk
                if clusterer and entities:
                    entity_ids = clusterer.batch_cluster_chunk_entities(entities, chunk_id)
                    self.semantic_store.persist_chunk_with_entities(chunk_id, entity_ids)
                
                all_entities.extend(entities)
                
                self.extraction_stats["chunks_processed"] += 1
                
                if self.domain_names == ["auto"]:
                    self.extraction_stats["auto_classifications"] += 1
                
                if self.extraction_stats["chunks_processed"] % 5 == 0:
                    logger.info(f"⏱️ Processed {self.extraction_stats['chunks_processed']}/{len(chunks)} chunks")
                
                log_memory_usage(f"After chunk {chunk.id}")
                
            except Exception as e:
                logger.error(f"💥 Error processing chunk {chunk.id}: {e}")
                if self.domain_names == ["auto"]:
                    self.extraction_stats["auto_classification_failures"] += 1
                continue
        
        # PHASE 3: Cross-chunk relationships
        if self.semantic_store and len(all_entities) > 0:
            try:
                logger.info(f"🔗 Discovering relationships...")
                relationships_count = self.semantic_store.discover_cross_chunk_relationships()
                logger.info(f"🔗 Discovered {relationships_count} relationships")
            except Exception as e:
                logger.warning(f"⚠️ Failed to discover relationships: {e}")
        
        # PHASE 4: Final deduplication
        logger.info(f"🔄 Final deduplication of {len(all_entities)} entities...")
        deduplicated_entities = _deduplicate_entities(all_entities)
        
        # PHASE 5: Save
        if self.semantic_store:
            try:
                self.semantic_store.save_to_disk()
                logger.info("💾 Semantic store saved")
            except Exception as e:
                logger.warning(f"⚠️ Failed to save: {e}")
        
        self._log_final_stats_with_chunks(deduplicated_entities, len(chunks))
        
        return deduplicated_entities
    
    def _log_final_stats_with_chunks(self, deduplicated_entities: List[ExtractedEntity], chunk_count: int):
        """Log stats"""
        validation_rate = (self.extraction_stats["entities_extracted_valid"] / 
                        self.extraction_stats["entities_extracted_raw"] 
                        if self.extraction_stats["entities_extracted_raw"] > 0 else 0)
        
        if self.domain_names == ["auto"]:
            auto_success_rate = ((self.extraction_stats["auto_classifications"] - 
                                self.extraction_stats["auto_classification_failures"]) / 
                                self.extraction_stats["auto_classifications"] 
                                if self.extraction_stats["auto_classifications"] > 0 else 0)
            
            logger.info(f"🎯 Batch auto-classification complete:")
            logger.info(f"  📊 Chunks: {self.extraction_stats['chunks_processed']}/{chunk_count}")
            logger.info(f"  ✅ Auto success: {auto_success_rate:.1%}")
        else:
            logger.info(f"🎯 Batch multi-domain complete:")
            logger.info(f"  📊 Chunks: {self.extraction_stats['chunks_processed']}/{chunk_count}")
            logger.info(f"  🗂️ Domains: {self.extraction_stats['domains_used']} {self.domain_names}")
        
        logger.info(f"  📝 Raw: {self.extraction_stats['entities_extracted_raw']}")
        logger.info(f"  ✅ Valid: {self.extraction_stats['entities_extracted_valid']}")
        logger.info(f"  🎯 Final: {len(deduplicated_entities)}")
        logger.info(f"  📊 Validation: {validation_rate:.1%}")
        
        if self.semantic_store:
            semantic_stats = self.semantic_store.get_stats()
            logger.info(f"  🧠 Dedup hits: {self.extraction_stats['semantic_deduplication_hits']}")
            logger.info(f"  💾 Stored entities: {semantic_stats['entities']}")
            logger.info(f"  📝 Stored chunks: {semantic_stats['chunks']}")
            logger.info(f"  🔗 Relationships: {semantic_stats['relationships']['total_relationships']}")
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        stats = self.extraction_stats.copy()
        stats.update(self.context_stats)
        stats.update(self.meta_prompt_stats)
        
        if stats["entities_extracted_raw"] > 0:
            stats["validation_rate"] = stats["entities_extracted_valid"] / stats["entities_extracted_raw"]
            stats["rejection_rate"] = stats["entities_rejected"] / stats["entities_extracted_raw"]
        else:
            stats["validation_rate"] = 0
            stats["rejection_rate"] = 0
        
        if self.semantic_store:
            stats["semantic_store"] = self.semantic_store.get_stats()
        
        return stats
    
    def get_semantic_store(self) -> Optional[SemanticStore]:
        """Get semantic store"""
        return self.semantic_store if self.enable_semantic_store else None