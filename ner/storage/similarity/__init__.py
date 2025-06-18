"""
ner/storage/similarity/__init__.py

Similarity components for weighted entity matching
Engine + Matrix operations + Weighted calculations
"""

from .engine import EntitySimilarityEngine
from .weighted import WeightedSimilarity
from .matrix_ops import MatrixOperations

__all__ = [
    'EntitySimilarityEngine',
    'WeightedSimilarity', 
    'MatrixOperations'
]