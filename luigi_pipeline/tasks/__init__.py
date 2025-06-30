# PLIK: luigi_pipeline/tasks/__init__.py
"""
Luigi tasks for NER pipeline
"""

from .conditional_processor import ConditionalProcessor

__all__ = [
    'ConditionalProcessor'
]