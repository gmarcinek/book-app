"""
Enhanced Entity Extractor with OpenAI embeddings
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
    evidence: str = ""
    
    def __post_init__(self):
        # Initialize aliases as empty list if None
        if self.aliases is None:
            self.aliases = []


class EntityExtractor:
    """Enhanced multi-domain entity extractor with OpenAI embeddings"""
    
    def __init__(self, 
               model: str = Models.QWEN_CODER, 
               config: Optional[NERConfig] = None,
               domain_names: List[str] = None,
               storage_dir: str = "semantic_store",
               enable_semantic_store: bool = True):
        
        # Initialize extractor with OpenAI embeddings
        self.config = config if config is not None else create_default_ner_config()
        self.model = model
        self.llm_client = None
        self.enable_semantic_store = enable_semantic_store
        
        if domain_names is None:
            domain_names = ["literary"]
        
        self.domain_names = domain_names
       
        if domain_names == ["auto"]:
            self.domains = []
            print("🤖 Initialized extractor with auto-classification mode")
        else:
            self.domains = DomainFactory.use(domain_names)
            print(f"🔄 Initialized extractor with domains: 🗂️ {domain_names}")
       
        # Initialize SemanticStore with OpenAI embeddings
        if self.enable_semantic_store:
            try:
                self.semantic_store = SemanticStore(
                    storage_dir=storage_dir,
                    embedding_model="text-embedding-3-small"  # OpenAI model
                )
                print(f"🧠 SemanticStore enabled with OpenAI embeddings: {storage_dir}")
            except Exception as e:
                print(f"⚠️ Failed to initialize SemanticStore: {e}")
                self.semantic_store = None
                self.enable_semantic_store = False
        else:
            self.semantic_store = None
            print("🚫 SemanticStore disabled")

        # Initialize EntityLinker
        self.entity_linker = EntityLinker(self.semantic_store)
        
        # Stats
        available_domains = ["literary", "simple", "owu", "financial"] if domain_names == ["auto"] else domain_names
       
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
        # Initialize LLM client if needed
        if self.llm_client is None:
            try:
                from llm import LLMClient
                self.llm_client = LLMClient(self.model)
                print(f"🤖 Initialized LLM model: {self.model}")
            except Exception as e:
                print(f"💥 Failed to initialize LLM: {e}")
                raise
   
    def _call_llm_for_meta_analysis(self, prompt: str) -> str:
        # Call LLM for meta-analysis
        try:
            if self.llm_client is None:
                self._initialize_llm()
            
            config = LLMConfig(
                temperature=self.config.get_meta_analysis_temperature()
            )
            
            response = self.llm_client.chat(prompt, config)
            return response
            
        except Exception as e:
            print(f"🔥 Meta-analysis LLM call failed: {e}")
            raise
   
    def _call_llm_for_entity_extraction(self, prompt: str) -> str:
        # Call LLM for entity extraction
        try:
            if self.llm_client is None:
                self._initialize_llm()
            
            config = LLMConfig(
                temperature=self.config.get_entity_extraction_temperature()
            )
            
            response = self.llm_client.chat(prompt, config)
            return response
            
        except Exception as e:
            print(f"🔥 Entity extraction LLM call failed: {e}")
            raise
   
    def _call_llm_for_auto_classification(self, prompt: str) -> str:
        # Call LLM for auto-classification
        try:
            if self.llm_client is None:
                self._initialize_llm()
            
            config = LLMConfig(
                temperature=self.config.get_auto_classification_temperature()
            )
            
            response = self.llm_client.chat(prompt, config)
            return response
            
        except Exception as e:
            print(f"🎯 Auto-classification LLM call failed: {e}")
            raise
    
    def extract_entities(self, chunks: List[TextChunk]) -> List[ExtractedEntity]:
        # Extract entities using OpenAI embeddings for similarity
        from .extraction import extract_entities_from_chunk_multi_domain
        from .deduplication import _deduplicate_entities
        from .batch_clustering import EntityBatchClusterer
        from .entity_linker import EntityLinker
        
        self._initialize_llm()
        
        all_entities = []
        chunk_ids_mapping = {}
        
        if self.domain_names == ["auto"]:
            print(f"🔄 Starting batch auto-classification from {len(chunks)} chunks")
        else:
            print(f"🔄 Starting batch multi-domain extraction from {len(chunks)} chunks")

        if hasattr(self, "aggregator") is False and hasattr(chunks[0], "aggregator"):
            self.aggregator = chunks[0].aggregator
        
        # PHASE 1: Register chunks
        if self.semantic_store:
            print(f"📝 Registering {len(chunks)} chunks...")
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
        
        # PHASE 2: Extract + batch cluster per chunk
        clusterer = EntityBatchClusterer(self.semantic_store, self.extraction_stats) if self.semantic_store else None
        
        for chunk in chunks:
            try:
                chunk_id = chunk_ids_mapping.get(chunk.id) if self.semantic_store else None
                
                # Extract entities and relationships
                entities, chunk_relationships = extract_entities_from_chunk_multi_domain(
                    self, chunk, self.domains, self.domain_names, chunk_id
                )
                
                for entity in entities:
                    entity.chunk_id = chunk.id
                    if chunk_id:
                        entity.semantic_chunk_id = chunk_id
                
                # Batch cluster entities using OpenAI embeddings
                if clusterer and entities:
                    entity_ids = clusterer.batch_cluster_chunk_entities(entities, chunk_id)
                    self.semantic_store.persist_chunk_with_entities(chunk_id, entity_ids)

                # Resolve relationships
                resolved_relationships = []
                for rel in chunk_relationships:
                    resolved = self.entity_linker.resolve_relationship(rel)
                    if resolved:
                        resolved_relationships.append(resolved)

                print(f"🔍 Relationships: {len(chunk_relationships)} raw → {len(resolved_relationships)} resolved")

                # Store resolved relationships
                if self.semantic_store and resolved_relationships:
                    for rel in resolved_relationships:
                        self.semantic_store.relationship_manager.add_structural_relationship(
                            rel['source_id'], rel['target_id'], rel['pattern'], 
                            rel['confidence'], evidence=rel['evidence']
                        )
                
                all_entities.extend(entities)
                self.extraction_stats["chunks_processed"] += 1
                
                if self.domain_names == ["auto"]:
                    self.extraction_stats["auto_classifications"] += 1
                
                if self.extraction_stats["chunks_processed"] % 5 == 0:
                    print(f"⏱️ Processed {self.extraction_stats['chunks_processed']}/{len(chunks)} chunks")
                
                log_memory_usage(f"After chunk {chunk.id}")
                
            except Exception as e:
                print(f"💥 Error processing chunk {chunk.id}: {e}")
                if self.domain_names == ["auto"]:
                    self.extraction_stats["auto_classification_failures"] += 1
                continue
        
        # PHASE 3: Cross-chunk relationships using OpenAI embeddings
        if self.semantic_store and len(all_entities) > 0:
            try:
                print(f"🔗 Discovering cross-chunk relationships...")
                relationships_count = self.semantic_store.discover_cross_chunk_relationships()
                print(f"🔗 Discovered {relationships_count} relationships")
            except Exception as e:
                print(f"⚠️ Failed to discover relationships: {e}")
        
        # PHASE 4: Final deduplication
        print(f"🔄 Final deduplication of {len(all_entities)} entities...")
        deduplicated_entities = _deduplicate_entities(all_entities)
        
        # PHASE 5: Save
        if self.semantic_store:
            try:
                self.semantic_store.save_to_disk()
                print("💾 Semantic store saved")
            except Exception as e:
                print(f"⚠️ Failed to save: {e}")
        
        self._log_final_stats_with_chunks(deduplicated_entities, len(chunks))
        return deduplicated_entities
    
    def _log_final_stats_with_chunks(self, deduplicated_entities: List[ExtractedEntity], chunk_count: int):
        # Log final extraction statistics
        validation_rate = (self.extraction_stats["entities_extracted_valid"] / 
                        self.extraction_stats["entities_extracted_raw"] 
                        if self.extraction_stats["entities_extracted_raw"] > 0 else 0)
        
        if self.domain_names == ["auto"]:
            auto_success_rate = ((self.extraction_stats["auto_classifications"] - 
                                self.extraction_stats["auto_classification_failures"]) / 
                                self.extraction_stats["auto_classifications"] 
                                if self.extraction_stats["auto_classifications"] > 0 else 0)
            
            print(f"🎯 Batch auto-classification complete:")
            print(f"  📊 Chunks: {self.extraction_stats['chunks_processed']}/{chunk_count}")
            print(f"  ✅ Auto success: {auto_success_rate:.1%}")
        else:
            print(f"🎯 Batch multi-domain complete:")
            print(f"  📊 Chunks: {self.extraction_stats['chunks_processed']}/{chunk_count}")
            print(f"  🗂️ Domains: {self.extraction_stats['domains_used']} {self.domain_names}")
        
        print(f"  📝 Raw: {self.extraction_stats['entities_extracted_raw']}")
        print(f"  ✅ Valid: {self.extraction_stats['entities_extracted_valid']}")
        print(f"  🎯 Final: {len(deduplicated_entities)}")
        print(f"  📊 Validation: {validation_rate:.1%}")
        
        if self.semantic_store:
            semantic_stats = self.semantic_store.get_stats()
            print(f"  🧠 Dedup hits: {self.extraction_stats['semantic_deduplication_hits']}")
            print(f"  💾 Stored entities: {semantic_stats['entities']}")
            print(f"  📝 Stored chunks: {semantic_stats['chunks']}")
            print(f"  🔗 Relationships: {semantic_stats['relationships']['total_relationships']}")
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        # Get extraction statistics
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
        # Get semantic store instance
        return self.semantic_store if self.enable_semantic_store else None