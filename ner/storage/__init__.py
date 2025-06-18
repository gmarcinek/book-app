"""
ner/storage/__init__.py

Storage module for semantic entity management with FAISS and NetworkX
Enhanced with clustering-based deduplication
"""

from .models import StoredEntity, StoredChunk, EntityRelationship, RelationType
from .embedder import EntityEmbedder
from .indices import FAISSManager
from .relations import RelationshipManager
from .persistence import StoragePersistence
from .store import SemanticStore

# New clustering components
from .clustering.union_find import EntityUnionFind
from .clustering.merger import EntityMerger
from .similarity.engine import EntitySimilarityEngine

__all__ = [
    'StoredEntity',
    'StoredChunk', 
    'EntityRelationship',
    'RelationType',
    'EntityEmbedder',
    'FAISSManager',
    'RelationshipManager',
    'StoragePersistence',
    'SemanticStore',
    # New clustering components
    'EntityUnionFind',
    'EntityMerger',
    'EntitySimilarityEngine'
]