"""
ner/extractor/base.py

Enhanced Entity Extractor with SemanticStore integration for real-time semantic enhancement
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

# Local imports
from ..utils import log_memory_usage
from ..semantic import TextChunk
from ..domains import DomainFactory, BaseNER
from ..config import NERConfig, create_default_ner_config
from ..storage import SemanticStore
from llm import Models, LLMConfig

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
    """
    Enhanced multi-domain entity extractor with semantic store integration
    
    Features:
    - Real-time semantic enhancement via SemanticStore
    - Cross-document entity deduplication
    - Contextual entity discovery for better NER prompts
    - Auto-classification support with semantic memory
    """
    
    def __init__(self, 
                 model: str = Models.QWEN_CODER, 
                 config: Optional[NERConfig] = None,
                 domain_names: List[str] = None,
                 storage_dir: str = "semantic_store",
                 enable_semantic_store: bool = True):
        
        # Use provided config or create default
        self.config = config if config is not None else create_default_ner_config()
        
        self.model = model
        self.llm_client = None
        self.enable_semantic_store = enable_semantic_store
        
        # Handle domain names
        if domain_names is None:
            domain_names = ["literary", "liric"]
        
        self.domain_names = domain_names
        
        # For auto mode, we don't pre-create domains (they'll be determined per chunk)
        if domain_names == ["auto"]:
            self.domains = []  # Will be populated per chunk
            logger.info("🤖 Initialized extractor with auto-classification mode")
        else:
            # Regular multi-domain mode
            self.domains = DomainFactory.use(domain_names)
            logger.info(f"🔄 Initialized extractor with domains: 🗂️ {domain_names}")
        
        # Initialize SemanticStore for real-time enhancement
        if self.enable_semantic_store:
            try:
                self.semantic_store = SemanticStore(
                    storage_dir=storage_dir,
                    embedding_model="sentence-transformers/all-MiniLM-L6-v2"
                )
                logger.info(f"🧠 SemanticStore enabled: {storage_dir}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize SemanticStore: {e}, proceeding without semantic enhancement")
                self.semantic_store = None
                self.enable_semantic_store = False
        else:
            self.semantic_store = None
            logger.info("🚫 SemanticStore disabled")
        
        # Stats - initialize with available domains for non-auto mode
        if domain_names == ["auto"]:
            # For auto mode, initialize with all possible domains
            available_domains = ["literary", "liric", "simple", "owu"]
        else:
            available_domains = domain_names
        
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
            
            return self.llm_client.chat(prompt, config)
            
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
            
            return self.llm_client.chat(prompt, config)
            
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
            
            return self.llm_client.chat(prompt, config)
            
        except Exception as e:
            logger.error(f"🎯 Auto-classification LLM call failed: {e}")
            raise
    
    def extract_entities(self, chunks: List[TextChunk]) -> List[ExtractedEntity]:
        """
        Extract entities from multiple text chunks using domains or auto-classification
        Enhanced with semantic store integration
        """
        from .extraction import extract_entities_from_chunk_multi_domain
        from .deduplication import _deduplicate_entities
        
        self._initialize_llm()
        
        all_entities = []
        
        if self.domain_names == ["auto"]:
            logger.info(f"🔄 Starting auto-classification extraction from {len(chunks)} chunks")
        else:
            logger.info(f"🔄 Starting multi-domain extraction from {len(chunks)} chunks using {len(self.domains)} domains")

        if hasattr(self, "aggregator") is False and hasattr(chunks[0], "aggregator"):
            self.aggregator = chunks[0].aggregator
        
        for chunk in chunks:
            try:
                # PHASE 1: Register chunk in semantic store (if enabled)
                chunk_id = None
                if self.semantic_store:
                    chunk_data = {
                        'id': f"chunk_{chunk.id}",
                        'text': chunk.text,
                        'document_source': getattr(chunk, 'document_source', 'unknown'),
                        'start_pos': chunk.start,
                        'end_pos': chunk.end,
                        'chunk_index': chunk.id
                    }
                    chunk_id = self.semantic_store.register_chunk(chunk_data)
                
                # PHASE 2: Extract with semantic enhancement
                entities = extract_entities_from_chunk_multi_domain(
                    self, chunk, self.domains, self.domain_names, chunk_id
                )
                all_entities.extend(entities)
                
                # PHASE 3: Persist chunk with entities (if semantic store enabled)
                if self.semantic_store and chunk_id:
                    entity_ids = [getattr(entity, 'semantic_store_id', None) for entity in entities]
                    entity_ids = [eid for eid in entity_ids if eid]  # Filter None values
                    
                    if entity_ids:
                        self.semantic_store.persist_chunk_with_entities(chunk_id, entity_ids)
                
                self.extraction_stats["chunks_processed"] += 1
                
                # Track auto-classification stats
                if self.domain_names == ["auto"]:
                    self.extraction_stats["auto_classifications"] += 1
                
                # Log progress every 5 chunks
                if self.extraction_stats["chunks_processed"] % 5 == 0:
                    logger.info(f"⏱️ Processed {self.extraction_stats['chunks_processed']}/{len(chunks)} chunks")
                
                # Memory management
                log_memory_usage(f"After chunk {chunk.id}")
                
            except Exception as e:
                logger.error(f"💥 Error processing chunk {chunk.id}: {e}")
                if self.domain_names == ["auto"]:
                    self.extraction_stats["auto_classification_failures"] += 1
                continue
        
        # Discover cross-chunk relationships (if semantic store enabled)
        if self.semantic_store and len(all_entities) > 0:
            try:
                relationships_count = self.semantic_store.discover_cross_chunk_relationships()
                logger.info(f"🔗 Discovered {relationships_count} cross-chunk relationships")
            except Exception as e:
                logger.warning(f"⚠️ Failed to discover cross-chunk relationships: {e}")
        
        # Deduplicate entities (using traditional method as final cleanup)
        logger.info(f"🔄 Final deduplication of {len(all_entities)} entities...")
        deduplicated_entities = _deduplicate_entities(all_entities)
        
        # Save semantic store state
        if self.semantic_store:
            try:
                self.semantic_store.save_to_disk()
                logger.info("💾 Semantic store saved successfully")
            except Exception as e:
                logger.warning(f"⚠️ Failed to save semantic store: {e}")
        
        # Final stats
        self._log_final_stats(deduplicated_entities)
        
        return deduplicated_entities
    
    def _log_final_stats(self, deduplicated_entities: List[ExtractedEntity]):
        """Log comprehensive extraction statistics"""
        validation_rate = (self.extraction_stats["entities_extracted_valid"] / 
                          self.extraction_stats["entities_extracted_raw"] 
                          if self.extraction_stats["entities_extracted_raw"] > 0 else 0)
        
        context_accuracy = (self.context_stats["entities_found_in_context"] / 
                           self.context_stats["contexts_generated"] 
                           if self.context_stats["contexts_generated"] > 0 else 0)
        
        meta_success_rate = ((self.meta_prompt_stats['meta_prompts_generated'] - 
                             self.meta_prompt_stats['meta_prompts_failed']) / 
                            self.meta_prompt_stats['meta_prompts_generated'] 
                            if self.meta_prompt_stats['meta_prompts_generated'] > 0 else 0)
        
        # Mode-specific logging
        if self.domain_names == ["auto"]:
            auto_success_rate = ((self.extraction_stats["auto_classifications"] - 
                                 self.extraction_stats["auto_classification_failures"]) / 
                                self.extraction_stats["auto_classifications"] 
                                if self.extraction_stats["auto_classifications"] > 0 else 0)
            
            logger.info(f"🎯 Auto-classification extraction complete:")
            logger.info(f"  📊 Chunks processed: {self.extraction_stats['chunks_processed']}")
            logger.info(f"  🤖 Auto-classifications: {self.extraction_stats['auto_classifications']}")
            logger.info(f"  ✅ Auto-classification success rate: {auto_success_rate:.1%}")
        else:
            logger.info(f"🎯 Multi-domain extraction complete:")
            logger.info(f"  📊 Chunks processed: {self.extraction_stats['chunks_processed']}")
            logger.info(f"  🗂️ Domains used: {self.extraction_stats['domains_used']} {self.domain_names}")
        
        logger.info(f"  📝 Raw entities: {self.extraction_stats['entities_extracted_raw']}")
        logger.info(f"  ✅ Valid entities: {self.extraction_stats['entities_extracted_valid']}")
        logger.info(f"  🎯 Final entities (after dedup): {len(deduplicated_entities)}")
        logger.info(f"  📊 Validation rate: {validation_rate:.1%}")
        logger.info(f"  🎯 Context accuracy: {context_accuracy:.1%}")
        logger.info(f"  🧠 Meta-prompt success rate: {meta_success_rate:.1%}")
        
        # Semantic store stats
        if self.semantic_store:
            semantic_stats = self.semantic_store.get_stats()
            logger.info(f"  🧠 Semantic enhancements: {self.extraction_stats['semantic_enhancements']}")
            logger.info(f"  🔗 Semantic deduplication hits: {self.extraction_stats['semantic_deduplication_hits']}")
            logger.info(f"  💾 Stored entities: {semantic_stats['entities']}")
            logger.info(f"  📝 Stored chunks: {semantic_stats['chunks']}")
        
        # Per-domain stats (only for domains that were actually used)
        domains_used = set(entity.domain for entity in deduplicated_entities if entity.domain)
        for domain_name in domains_used:
            domain_stats = self.extraction_stats["by_domain"].get(domain_name, {"raw": 0, "valid": 0})
            domain_rate = (domain_stats["valid"] / domain_stats["raw"] 
                          if domain_stats["raw"] > 0 else 0)
            logger.info(f"  🏷️ Domain '{domain_name}': {domain_stats['raw']} raw → {domain_stats['valid']} valid ({domain_rate:.1%})")
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get detailed extraction statistics including semantic store"""
        stats = self.extraction_stats.copy()
        stats.update(self.context_stats)
        stats.update(self.meta_prompt_stats)
        
        # Overall rates
        if stats["entities_extracted_raw"] > 0:
            stats["validation_rate"] = stats["entities_extracted_valid"] / stats["entities_extracted_raw"]
            stats["rejection_rate"] = stats["entities_rejected"] / stats["entities_extracted_raw"]
        else:
            stats["validation_rate"] = 0
            stats["rejection_rate"] = 0
        
        if stats["contexts_generated"] > 0:
            stats["context_accuracy"] = stats["entities_found_in_context"] / stats["contexts_generated"]
            stats["fallback_rate"] = stats["fallback_contexts_used"] / stats["contexts_generated"]
        else:
            stats["context_accuracy"] = 0
            stats["fallback_rate"] = 0
        
        if stats["meta_prompts_generated"] > 0:
            stats["meta_prompt_success_rate"] = ((stats["meta_prompts_generated"] - stats["meta_prompts_failed"]) / 
                                                stats["meta_prompts_generated"])
        else:
            stats["meta_prompt_success_rate"] = 0
        
        # Auto-classification rates
        if stats["auto_classifications"] > 0:
            stats["auto_classification_success_rate"] = ((stats["auto_classifications"] - stats["auto_classification_failures"]) / 
                                                        stats["auto_classifications"])
        else:
            stats["auto_classification_success_rate"] = 0
        
        # Semantic enhancement rates
        if self.semantic_store and stats["chunks_processed"] > 0:
            stats["semantic_enhancement_rate"] = stats["semantic_enhancements"] / stats["chunks_processed"]
            stats["semantic_deduplication_rate"] = stats["semantic_deduplication_hits"] / stats["entities_extracted_raw"] if stats["entities_extracted_raw"] > 0 else 0
        else:
            stats["semantic_enhancement_rate"] = 0
            stats["semantic_deduplication_rate"] = 0
        
        # Add semantic store stats if available
        if self.semantic_store:
            stats["semantic_store"] = self.semantic_store.get_stats()
        
        return stats
    
    def get_semantic_store(self) -> Optional[SemanticStore]:
        """Get access to semantic store for external operations"""
        return self.semantic_store if self.enable_semantic_store else None
    
    def extract_entities_from_chunk_multi_domain(extractor, chunk, domains, domain_names):
        """Temporary stub to fix imports"""
        return []