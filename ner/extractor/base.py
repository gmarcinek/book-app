"""
Base Entity Extractor - multi-domain extraction with Auto-Classification support
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

# Local imports
from ..utils import load_ner_config, log_memory_usage
from ..chunker import TextChunk
from ..domains import DomainFactory, BaseNER
from llm import Models
from .config_extractor import ExtractorConfig

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
    domain: Optional[str] = None  # ← Which domain extracted this entity
    
    def __post_init__(self):
        """Initialize aliases as empty list if None"""
        if self.aliases is None:
            self.aliases = []


class EntityExtractor:
    """
    Multi-domain entity extractor with auto-classification support
    """
    
    def __init__(self, 
                 model: str = Models.QWEN_CODER, 
                 config_path: str = "ner/ner_config.json",
                 domain_names: List[str] = None):
        
        self.config = load_ner_config(config_path)
        self.extractor_config = ExtractorConfig()
        self.model = model
        self.llm_client = None
        
        # Handle domain names
        if domain_names is None:
            domain_names = ["literary", "liric"]
        
        self.domain_names = domain_names
        
        # For auto mode, we don't pre-create domains (they'll be determined per chunk)
        if domain_names == ["auto"]:
            self.domains = []  # Will be populated per chunk
            logger.info("Initialized extractor with auto-classification mode")
        else:
            # Regular multi-domain mode
            self.domains = DomainFactory.use(domain_names)
            logger.info(f"🔄 Initialized extractor with domains: 🗂️ {domain_names}")
        
        # Stats - initialize with available domains for non-auto mode
        if domain_names == ["auto"]:
            # For auto mode, initialize with all possible domains
            available_domains = ["literary", "liric", "simple"]
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
                logger.error(f"❌ Failed to initialize LLM: {e}")
                raise
    
    def _call_llm(self, prompt: str, temperature: Optional[float] = None) -> str:
        """Call LLM with prompt and return response"""
        try:
            if self.llm_client is None:
                self._initialize_llm()
            
            if temperature is not None:
                from llm import LLMConfig
                config = LLMConfig(
                    max_tokens=self.extractor_config.get_max_tokens(),
                    temperature=temperature
                )
                response = self.llm_client.chat(prompt, config)
            else:
                response = self.llm_client.chat(prompt)
            
            return response
            
        except Exception as e:
            logger.error(f"❌ LLM call failed: {e}")
            raise
    
    def extract_entities(self, chunks: List[TextChunk]) -> List[ExtractedEntity]:
        """Extract entities from multiple text chunks using domains or auto-classification"""
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
                # Extract with domains (or auto-classification)
                entities = extract_entities_from_chunk_multi_domain(self, chunk, self.domains, self.domain_names)
                all_entities.extend(entities)
                
                self.extraction_stats["chunks_processed"] += 1
                
                # Track auto-classification stats
                if self.domain_names == ["auto"]:
                    self.extraction_stats["auto_classifications"] += 1
                
                # Log progress every 5 chunks
                if self.extraction_stats["chunks_processed"] % 5 == 0:
                    logger.info(f"Processed {self.extraction_stats['chunks_processed']}/{len(chunks)} chunks")
                
                # Memory management
                log_memory_usage(f"After chunk {chunk.id}")
                
            except Exception as e:
                logger.error(f"❌ Error processing chunk {chunk.id}: {e}")
                if self.domain_names == ["auto"]:
                    self.extraction_stats["auto_classification_failures"] += 1
                continue
        
        # Deduplicate entities (across domains)
        logger.info(f"Deduplicating {len(all_entities)} entities across domains...")
        deduplicated_entities = _deduplicate_entities(all_entities)
        
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
            
            logger.info(f"🟢 Auto-classification extraction complete:")
            logger.info(f"  Chunks processed: {self.extraction_stats['chunks_processed']}")
            logger.info(f"  Auto-classifications: {self.extraction_stats['auto_classifications']}")
            logger.info(f"  Auto-classification success rate: {auto_success_rate:.1%}")
        else:
            logger.info(f"🟢 Multi-domain extraction complete:")
            logger.info(f"  Chunks processed: {self.extraction_stats['chunks_processed']}")
            logger.info(f"  Domains used: {self.extraction_stats['domains_used']} {self.domain_names}")
        
        logger.info(f"  Raw entities: {self.extraction_stats['entities_extracted_raw']}")
        logger.info(f"  Valid entities: {self.extraction_stats['entities_extracted_valid']}")
        logger.info(f"  Final entities (after dedup): {len(deduplicated_entities)}")
        logger.info(f"  Validation rate: {validation_rate:.1%}")
        logger.info(f"  Context accuracy: {context_accuracy:.1%}")
        logger.info(f"  Meta-prompt success rate: {meta_success_rate:.1%}")
        
        # Per-domain stats (only for domains that were actually used)
        domains_used = set(entity.domain for entity in deduplicated_entities if entity.domain)
        for domain_name in domains_used:
            domain_stats = self.extraction_stats["by_domain"].get(domain_name, {"raw": 0, "valid": 0})
            domain_rate = (domain_stats["valid"] / domain_stats["raw"] 
                          if domain_stats["raw"] > 0 else 0)
            logger.info(f"  Domain '{domain_name}': {domain_stats['raw']} raw → {domain_stats['valid']} valid ({domain_rate:.1%})")
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get detailed extraction statistics including auto-classification"""
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
        
        return stats