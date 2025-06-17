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

# Import main pipeline functions
from .pipeline import (
    process_text_to_knowledge, 
    process_file, 
    process_directory, 
    NERProcessingError
)

# Version info
__version__ = "0.5.0"  # Bumped version for SemanticStore-based release
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
    
    # Data classes
    'TextChunk',
    'LoadedDocument',
    
    # Utilities
    'load_text',
    'log_memory_usage',
    
    # Version
    '__version__'
]