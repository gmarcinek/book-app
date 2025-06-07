"""
NER (Named Entity Recognition) Package - Uproszczona wersja

A simplified package for extracting entities from text using LLMs.
Supports multiple document formats and provides basic knowledge representation.
"""

# Import all components (bez relacji)
from .loaders import DocumentLoader, LoadedDocument, load_text
from .chunker import TextChunker, TextChunk
from .extractor import EntityExtractor
from .aggregator import GraphAggregator
from .resolver import EntityResolver  # Placeholder
from .utils import load_ner_config, log_memory_usage
from .prompts import NERPrompts
from .consts import ENTITY_TYPES, PHENOMENON_PREFIXES
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
__version__ = "0.3.0"  # Bumped version for simplified release
__author__ = "NER Team"

# Public API - uproszczone
__all__ = [
    # Main pipeline functions
    'process_text_to_knowledge',
    'process_file', 
    'process_directory',
    'validate_configuration',
    'NERProcessingError',
    
    # Core components (bez relationships i validation)
    'EntityExtractor',
    'GraphAggregator',
    'EntityResolver',  # Placeholder
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
    'ENTITY_TYPES',
    'PHENOMENON_PREFIXES',
    'call_llm_semantic_cleaning',
    
    # Version
    '__version__'
]