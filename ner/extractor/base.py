# ner/extractor/base.py
"""
Enhanced Entity Extractor - CLEAN VERSION without deduplication
Simple extraction with SemanticStore integration
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
    semantic_store_id: Optional[str] = None  # ID in semantic store
    
    def __post_init__(self):
        # Initialize aliases as empty list if None
        if self.aliases is None:
            self.aliases = []


class EntityExtractor:
    """Enhanced multi-domain entity extractor - CLEAN VERSION"""
    
    def __init__(self, 
                 model: str = Models.QWEN_CODER, 
                 config: Optional[NERConfig] = None,
                 domain_names: List[str] = None,
                 storage_dir: str = "semantic_store",
                 enable_semantic_store: bool = True):
        
        # Initialize extractor
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
       
        # Initialize SemanticStore
        if self.enable_semantic_store:
            try:
                self.semantic_store = SemanticStore(
                    storage_dir=storage_dir,
                    embedding_model="text-embedding-3-small"
                )
                print(f"🏗️ SemanticStore initialized at {storage_dir}")
            except Exception as e:
                print(f"⚠️ Failed to initialize SemanticStore: {e}")
                self.semantic_store = None
        else:
            self.semantic_store = None
            
        # Initialize statistics
        self.extraction_stats = {
            "chunks_processed": 0,
            "entities_extracted_raw": 0,
            "entities_extracted_valid": 0,
            "entities_rejected": 0,
            "by_domain": {}
        }
        
        self.meta_prompt_stats = {
            "meta_prompts_generated": 0,
            "meta_prompts_failed": 0,
            "fallback_to_standard_prompt": 0,
            "by_domain": {}
        }
        
        self.context_stats = {
            "contexts_generated": 0,
            "entities_found_in_context": 0,
            "fallback_contexts_used": 0
        }
        
        # Initialize domain stats
        for domain_name in self.domain_names:
            self.extraction_stats["by_domain"][domain_name] = {"raw": 0, "valid": 0}
            self.meta_prompt_stats["by_domain"][domain_name] = {"generated": 0, "failed": 0}

    def get_semantic_store(self) -> Optional[SemanticStore]:
        """Get the semantic store instance"""
        return self.semantic_store

    def _initialize_llm(self):
        """Initialize LLM client with fresh context every request to prevent context bleeding"""
        if self.llm_client is None:
            from llm import LLMClient
            self.llm_client = LLMClient(self.model, fresh_client_every_request=True)
            print(f"🤖 LLM initialized: {self.model} (fresh_client_every_request=True)")
   
    def _call_llm_for_meta_analysis(self, prompt: str) -> str:
        """Call LLM for meta-analysis"""
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
        """Call LLM for entity extraction"""
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
        """Call LLM for auto-classification"""
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
        """Extract entities using simple approach - NO deduplication"""
        from .extraction import extract_entities_from_chunk_multi_domain
        
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
            print(f"📝 Registering {len(chunks)} chunks in SemanticStore")
            for chunk in chunks:
                chunk_id = self.semantic_store.register_chunk({
                    'text': chunk.text,
                    'start': chunk.start,
                    'end': chunk.end,
                    'index': chunk.id,
                    'document_source': getattr(chunk, 'document_source', 'unknown'),
                    'metadata': getattr(chunk, 'metadata', {})
                })
                chunk_ids_mapping[chunk.id] = chunk_id
        
        # PHASE 2: Extract entities from each chunk
        for chunk in chunks:
            print(f"\n📄 Processing chunk {chunk.id}: {len(chunk.text):,} chars")
            
            try:
                # Extract entities and relationships
                chunk_entities, chunk_relationships = extract_entities_from_chunk_multi_domain(
                    self,
                    chunk, 
                    self.domains,
                    self.domain_names,
                    chunk_id=chunk_ids_mapping.get(chunk.id)
                )
                
                # Process entities - simple validation and storage
                for entity in chunk_entities:
                    if self._validate_entity(entity):
                        # Add to semantic store directly
                        if self.semantic_store:
                            self._add_entity_to_store(entity, chunk_ids_mapping.get(chunk.id))
                        
                        all_entities.append(entity)
                
                # Process relationships
                if chunk_relationships and self.semantic_store:
                    self._process_relationships(chunk_relationships)
                
                print(f"✅ Found {len(chunk_entities)} entities, {len(chunk_relationships)} relationships")
                self.extraction_stats["chunks_processed"] += 1
                
            except Exception as e:
                print(f"❌ Error processing chunk {chunk.id}: {e}")
                continue
        
        print(f"\n🎯 FINAL: Extracted {len(all_entities)} entities total")
        
        # Save semantic store
        if self.semantic_store:
            self.semantic_store.save_to_disk()
            print(f"💾 Saved semantic store to disk")
        
        return all_entities

    def _validate_entity(self, entity: ExtractedEntity) -> bool:
        """Simple entity validation"""
        if not entity.name or not entity.type:
            return False
        if entity.confidence < 0.2:  # Basic confidence threshold
            return False
        if len(entity.name.strip()) < 2:
            return False
        return True

    def _add_entity_to_store(self, entity: ExtractedEntity, chunk_id: str):
        """Add entity to semantic store without deduplication"""
        from ..storage.models import StoredEntity, create_entity_id
        
        # Create entity directly
        entity_id = create_entity_id(entity.name, entity.type)
        
        stored_entity = StoredEntity(
            id=entity_id,
            name=entity.name,
            type=entity.type,
            description=entity.description,
            confidence=entity.confidence,
            aliases=entity.aliases,
            context=entity.context or ""
        )
        
        # Add chunk reference
        if chunk_id:
            stored_entity.add_source_chunk(chunk_id)
            # Get document source from chunk
            if chunk_id in self.semantic_store.chunks:
                doc_source = self.semantic_store.chunks[chunk_id].document_source
                stored_entity.add_document_source(doc_source)
        
        # Add to store (no deduplication)
        self.semantic_store.add_entity(stored_entity)
        
        # Update ExtractedEntity with ID
        entity.semantic_store_id = entity_id

    def _process_relationships(self, relationships: List[Dict]):
        """Process relationships - simplified without EntityLinker"""
        if not self.semantic_store or not relationships:
            return
        
        # Simple relationship processing without complex linking
        for relationship in relationships:
            try:
                # Basic relationship validation
                if 'source' in relationship and 'target' in relationship:
                    # For now, just log relationships - can implement simple linking later
                    logger.info(f"Relationship found: {relationship['source']} -> {relationship['target']}")
            except Exception as e:
                logger.warning(f"Failed to process relationship: {e}")

    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        return {
            "extraction": self.extraction_stats,
            "meta_prompts": self.meta_prompt_stats,
            "context": self.context_stats,
            "failed_extractions": 0,
            "semantic_enhancements": 0,
        }

    def print_final_stats(self):
        """Print final extraction statistics"""
        stats = self.get_extraction_stats()
        
        print(f"\n📊 EXTRACTION STATISTICS:")
        print(f"   📄 Chunks processed: {stats['extraction']['chunks_processed']}")
        print(f"   🎯 Entities extracted (raw): {stats['extraction']['entities_extracted_raw']}")
        print(f"   ✅ Entities extracted (valid): {stats['extraction']['entities_extracted_valid']}")
        print(f"   ❌ Entities rejected: {stats['extraction']['entities_rejected']}")
        
        print(f"\n📊 BY DOMAIN:")
        for domain, counts in stats['extraction']['by_domain'].items():
            print(f"   🗂️ {domain}: {counts['valid']}/{counts['raw']} valid")
        
        print(f"\n📊 META-PROMPTS:")
        print(f"   🧠 Generated: {stats['meta_prompts']['meta_prompts_generated']}")
        print(f"   ❌ Failed: {stats['meta_prompts']['meta_prompts_failed']}")
        print(f"   🔄 Fallbacks: {stats['meta_prompts']['fallback_to_standard_prompt']}")