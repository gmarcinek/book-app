"""
Domain-specific NER implementations
"""

from .base import BaseNER, DomainConfig, DomainFactory
from .literary import LiteraryNER

__all__ = [
    'BaseNER',
    'DomainConfig', 
    'DomainFactory',
    'LiteraryNER'
]