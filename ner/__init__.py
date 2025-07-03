# ner/__init__.py
"""
NER (Named Entity Recognition) Package - SemanticStore-based version

A multi-domain package for extracting entities from text using LLMs.
Supports multiple document formats and domain-specific extraction strategies.
Enhanced with semantic similarity and cross-document knowledge persistence.
"""

# Import all components
from .loaders import DocumentLoader, LoadedDocument, load_text
from .semantic import TextChunker, TextChunk
from .extractor import EntityExtractor
from .storage import SemanticStore
from .resolver import EntityResolver  # Placeholder
from .utils import log_memory_usage

# Import domain system
from .domains import DomainFactory, BaseNER, DomainConfig

# Import config system
from .config import NERConfig, create_default_ner_config

# Import entity types and configuration - now from ner.types
from .types import (
    EntityType,
    RelationType,
    DEFAULT_ENTITY_TYPES,
    DEFAULT_RELATIONSHIP_PATTERNS,
    CORE_RELATIONSHIP_TYPES,
    DEFAULT_CONFIDENCE_THRESHOLDS,
    get_all_entity_types,
    get_all_relationship_types,
    get_confidence_threshold_for_type
)

# Import main pipeline functions
from .pipeline import (
    process_text_to_knowledge, 
    process_file, 
    process_directory, 
    NERProcessingError
)

# Legacy functions for backward compatibility
def extend_entity_types(base_types: list, additional_types: list) -> list:
    """Extend base entity types with domain-specific types"""
    return list(set(base_types + additional_types))

def extend_relationship_patterns(base_patterns: list, additional_patterns: list) -> list:
    """Extend base relationship patterns with domain-specific patterns"""
    return list(set(base_patterns + additional_patterns))

# Version info
__version__ = "0.6.0"  # Bumped version for deduplication removal
__author__ = "NER Team"

# Public API - SemanticStore-based
__all__ = [
    # Main pipeline functions
    'process_text_to_knowledge',
    'process_file', 
    'process_directory',
    'NERProcessingError',
    
    # Core components
    'EntityExtractor',
    'SemanticStore',
    'EntityResolver',  # Placeholder
    'TextChunker',
    'DocumentLoader',
    
    # Domain system
    'DomainFactory',
    'BaseNER',
    'DomainConfig',
    
    # Config system
    'NERConfig',
    'create_default_ner_config',
    
    # Entity types and configuration
    'EntityType',
    'RelationType',
    'DEFAULT_ENTITY_TYPES',
    'DEFAULT_RELATIONSHIP_PATTERNS',
    'CORE_RELATIONSHIP_TYPES',
    'DEFAULT_CONFIDENCE_THRESHOLDS',
    'get_all_entity_types',
    'get_all_relationship_types',
    'get_confidence_threshold_for_type',
    'extend_entity_types',
    'extend_relationship_patterns',
    
    # Data classes
    'TextChunk',
    'LoadedDocument',
    
    # Utilities
    'load_text',
    'log_memory_usage',
    
    # Version
    '__version__'
]