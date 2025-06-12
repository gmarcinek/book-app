"""
NER (Named Entity Recognition) Package - Domain-based version

A multi-domain package for extracting entities from text using LLMs.
Supports multiple document formats and domain-specific extraction strategies.
"""

# Import all components
from .loaders import DocumentLoader, LoadedDocument, load_text
from .chunker import TextChunker, TextChunk
from .extractor import EntityExtractor
from .aggregation import GraphAggregator
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
__version__ = "0.4.0"  # Bumped version for domain-based release
__author__ = "NER Team"

# Public API - domain-based
__all__ = [
    # Main pipeline functions
    'process_text_to_knowledge',
    'process_file', 
    'process_directory',
    'NERProcessingError',
    
    # Core components
    'EntityExtractor',
    'GraphAggregator',
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