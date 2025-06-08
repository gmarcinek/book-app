"""
Base Entity Extractor - główna klasa EntityExtractor + config temperatury
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

# Local imports
from ..utils import load_ner_config, log_memory_usage
from ..chunker import TextChunk
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
    
    def __post_init__(self):
        """Initialize aliases as empty list if None"""
        if self.aliases is None:
            self.aliases = []


class EntityExtractor:
    """
    Uproszczony ekstraktor encji - bez relacji + META-PROMPT SYSTEM
    """
    
    def __init__(self, model: str = Models.QWEN_CODER, config_path: str = "ner/ner_config.json"):
        self.config = load_ner_config(config_path)
        self.extractor_config = ExtractorConfig()
        self.model = model
        self.llm_client = None
        self.extraction_stats = {
            "chunks_processed": 0,
            "entities_extracted_raw": 0,
            "entities_extracted_valid": 0,
            "entities_rejected": 0,
            "failed_extractions": 0
        }
        self.context_stats = {
            'contexts_generated': 0,
            'entities_found_in_context': 0,
            'fallback_contexts_used': 0
        }
        # ← NOWE: stats dla meta-prompt systemu
        self.meta_prompt_stats = {
            'meta_prompts_generated': 0,
            'meta_prompts_failed': 0,
            'fallback_to_standard_prompt': 0
        }
    
    def _initialize_llm(self):
        """Initialize LLM client if needed"""
        if self.llm_client is None:
            try:
                from llm import LLMClient
                self.llm_client = LLMClient(self.model)
                logger.info(f"Initialized LLM model: {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize LLM: {e}")
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
            logger.error(f"LLM call failed: {e}")
            raise
    
    def extract_entities(self, chunks: List[TextChunk]) -> List[ExtractedEntity]:
        """Extract entities from multiple text chunks with deduplication"""
        from .extraction import _extract_entities_from_chunk
        from .deduplication import _deduplicate_entities
        
        self._initialize_llm()
        
        all_entities = []
        
        logger.info(f"Starting entity extraction from {len(chunks)} chunks")
        
        for chunk in chunks:
            try:
                entities = _extract_entities_from_chunk(self, chunk)
                all_entities.extend(entities)
                
                self.extraction_stats["chunks_processed"] += 1
                
                # Log progress every 5 chunks
                if self.extraction_stats["chunks_processed"] % 5 == 0:
                    logger.info(f"Processed {self.extraction_stats['chunks_processed']}/{len(chunks)} chunks")
                
                # Memory management
                log_memory_usage(f"After chunk {chunk.id}")
                
            except Exception as e:
                logger.error(f"Error processing chunk {chunk.id}: {e}")
                continue
        
        # Deduplicate entities
        logger.info(f"Deduplicating {len(all_entities)} entities...")
        deduplicated_entities = _deduplicate_entities(all_entities)
        
        # Final stats
        validation_rate = (self.extraction_stats["entities_extracted_valid"] / 
                          self.extraction_stats["entities_extracted_raw"] 
                          if self.extraction_stats["entities_extracted_raw"] > 0 else 0)
        
        context_accuracy = (self.context_stats["entities_found_in_context"] / 
                           self.context_stats["contexts_generated"] 
                           if self.context_stats["contexts_generated"] > 0 else 0)
        
        # ← NOWE: Meta-prompt stats
        meta_success_rate = ((self.meta_prompt_stats['meta_prompts_generated'] - 
                             self.meta_prompt_stats['meta_prompts_failed']) / 
                            self.meta_prompt_stats['meta_prompts_generated'] 
                            if self.meta_prompt_stats['meta_prompts_generated'] > 0 else 0)
        
        logger.info(f"Entity extraction complete:")
        logger.info(f"  Chunks processed: {self.extraction_stats['chunks_processed']}")
        logger.info(f"  Raw entities: {self.extraction_stats['entities_extracted_raw']}")
        logger.info(f"  Valid entities: {self.extraction_stats['entities_extracted_valid']}")
        logger.info(f"  Final entities (after dedup): {len(deduplicated_entities)}")
        logger.info(f"  Validation rate: {validation_rate:.1%}")
        logger.info(f"  Context accuracy: {context_accuracy:.1%}")
        logger.info(f"  Meta-prompt success rate: {meta_success_rate:.1%}")
        logger.info(f"  Fallback to standard prompt: {self.meta_prompt_stats['fallback_to_standard_prompt']}")
        
        return deduplicated_entities
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get detailed extraction statistics"""
        stats = self.extraction_stats.copy()
        stats.update(self.context_stats)
        stats.update(self.meta_prompt_stats)  # ← NOWE
        
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
        
        # ← NOWE: Meta-prompt stats
        if stats["meta_prompts_generated"] > 0:
            stats["meta_prompt_success_rate"] = ((stats["meta_prompts_generated"] - stats["meta_prompts_failed"]) / 
                                                stats["meta_prompts_generated"])
        else:
            stats["meta_prompt_success_rate"] = 0
        
        return stats