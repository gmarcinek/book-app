"""
ner/storage/clustering/__init__.py

Clustering components for entity deduplication
Union-Find for grouping + EntityMerger for bulk merging
"""

from .union_find import EntityUnionFind
from .merger import EntityMerger

__all__ = [
    'EntityUnionFind',
    'EntityMerger'
]