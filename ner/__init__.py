"""
NER (Named Entity Recognition) Package

A comprehensive package for extracting entities and relationships from text using LLMs.
Supports multiple document formats and provides graph-based knowledge representation.
"""

# Import all components
from .loaders import DocumentLoader, LoadedDocument, load_text
from .chunker import TextChunker, TextChunk
from .extractor import EntityExtractor
from .relationships import RelationshipExtractor
from .aggregator import GraphAggregator
from .resolver import EntityResolver
from .validation import RelationshipValidator
from .utils import load_ner_config, log_memory_usage
from .prompts import NERPrompts
from .consts import RELATIONSHIP_TYPES, ENTITY_TYPES
from .llm_utils import call_llm_semantic_cleaning

# Import main pipeline functions
from .pipeline import (
    process_text_to_knowledge, 
    process_file, 
    process_directory, 
    validate_configuration,
    NERProcessingError
)

# Version info
__version__ = "0.2.0"
__author__ = "NER Team"

# Public API
__all__ = [
    # Main pipeline functions
    'process_text_to_knowledge',
    'process_file', 
    'process_directory',
    'validate_configuration',
    'NERProcessingError',
    
    # Core components
    'EntityExtractor',
    'RelationshipExtractor',
    'GraphAggregator',
    'EntityResolver',
    'RelationshipValidator',
    'TextChunker',
    'DocumentLoader',
    
    # Data classes
    'TextChunk',
    'LoadedDocument',
    
    # Utilities
    'load_text',
    'load_ner_config',
    'log_memory_usage',
    'NERPrompts',
    'RELATIONSHIP_TYPES',
    'ENTITY_TYPES',
    
    # Version
    '__version__'
]
__all__ += ['call_llm_semantic_cleaning']