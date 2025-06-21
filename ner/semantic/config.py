"""
ner/semantic/config.py

Centralized configuration for semantic processing and clustering
Now imports thresholds from entity_config.py instead of defining them locally
"""

from dataclasses import dataclass
from typing import Dict

# Import centralized deduplication config
from ..entity_config import DeduplicationConfig


@dataclass
class SemanticConfig:
    """
    Semantic processing parameters - now delegates to DeduplicationConfig
    Simplified to avoid duplication with entity_config.py
    """
    
    def get_threshold_for_type(self, entity_type: str) -> float:
        """Get similarity threshold for entity type - delegates to DeduplicationConfig"""
        return DeduplicationConfig.get_threshold_for_entity_type_string(entity_type)
    
    @property
    def base_similarity_threshold(self) -> float:
        """Base similarity threshold for initial candidate filtering"""
        return DeduplicationConfig.BASE_SIMILARITY_THRESHOLD
    
    @property
    def name_search_threshold(self) -> float:
        """Name-based entity search threshold"""
        return DeduplicationConfig.NAME_SEARCH_THRESHOLD
    
    @property
    def name_search_max_results(self) -> int:
        """Max results for name search"""
        return DeduplicationConfig.NAME_SEARCH_MAX_RESULTS
    
    @property
    def context_search_threshold(self) -> float:
        """Context-based entity search threshold"""
        return DeduplicationConfig.CONTEXT_SEARCH_THRESHOLD
    
    @property
    def context_search_max_results(self) -> int:
        """Max results for context search"""
        return DeduplicationConfig.CONTEXT_SEARCH_MAX_RESULTS
    
    @property
    def contextual_entities_threshold(self) -> float:
        """Contextual entities for NER enhancement"""
        return DeduplicationConfig.CONTEXTUAL_ENTITIES_THRESHOLD
    
    @property
    def contextual_entities_max_results(self) -> int:
        """Max contextual entities results"""
        return DeduplicationConfig.CONTEXTUAL_ENTITIES_MAX_RESULTS
    
    @property
    def cooccurrence_threshold(self) -> float:
        """Co-occurrence relationships threshold"""
        return DeduplicationConfig.COOCCURRENCE_THRESHOLD
    
    @property
    def max_content_overlap_bonus(self) -> float:
        """Content overlap bonus for weighted similarity"""
        return DeduplicationConfig.MAX_CONTENT_OVERLAP_BONUS


# Global default instance - singleton pattern for simplicity
_default_config = None

def get_default_semantic_config() -> SemanticConfig:
    """Get default semantic configuration (singleton)"""
    global _default_config
    if _default_config is None:
        _default_config = SemanticConfig()
    return _default_config

def set_semantic_config(config: SemanticConfig):
    """Override default semantic configuration"""
    global _default_config
    _default_config = config