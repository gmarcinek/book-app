"""
Unified NER Configuration - Single source of truth for all NER module settings
"""

from dataclasses import dataclass
from enum import Enum

class ChunkingStrategy(Enum):
    PERCENTILE = "percentile"
    HIERARCHICAL = "hierarchical"
    LINEAR = "linear"

@dataclass
class NERConfig:
    """
    Unified configuration for entire NER module.
    Contains all settings for extraction, chunking, and processing.
    """
    
    # LLM settings
    meta_analysis_temperature: float = 0.0
    entity_extraction_temperature: float = 0.0
    auto_classification_temperature: float = 0.0
    default_model: str = "gpt-4o-mini"  # Default model for processing

    
    # Chunking settings
    chunk_size: int = 9000
    chunk_overlap: int = 400
    chunking_mode: str = "semantic"
    semantic_strategy: ChunkingStrategy = ChunkingStrategy.PERCENTILE
    
    # Processing limits
    max_iterations: int = 100
    min_entity_length: int = 2
    max_entity_length: int = 100
    
    # Feature flags
    enable_memory_monitoring: bool = True
    
    # Getters for backward compatibility with ExtractorConfig API
    def get_meta_analysis_temperature(self) -> float:
        """Get temperature for meta-analysis phase"""
        return self.meta_analysis_temperature
    
    def get_entity_extraction_temperature(self) -> float:
        """Get temperature for entity extraction phase"""
        return self.entity_extraction_temperature

    def get_auto_classification_temperature(self) -> float:
        """Get temperature for auto-classification phase"""
        return self.auto_classification_temperature
    
    def get_default_model(self) -> str:
        """Get default model for processing"""
        return self.default_model
    
    def get_chunk_size(self) -> int:
        """Get chunk size for text processing"""
        return self.chunk_size
    
    def get_chunk_overlap(self) -> int:
        """Get chunk overlap size"""
        return self.chunk_overlap
    
    def get_max_iterations(self) -> int:
        """Get maximum processing iterations"""
        return self.max_iterations
    
    def get_min_entity_length(self) -> int:
        """Get minimum entity name length"""
        return self.min_entity_length
    
    def get_max_entity_length(self) -> int:
        """Get maximum entity name length"""
        return self.max_entity_length
    
    def is_memory_monitoring_enabled(self) -> bool:
        """Check if memory monitoring is enabled"""
        return self.enable_memory_monitoring

def create_default_ner_config() -> NERConfig:
    """Create default NER configuration"""
    return NERConfig()