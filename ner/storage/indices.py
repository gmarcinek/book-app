"""
FAISS indices management with SemanticConfig thresholds
Dual entity embeddings and chunk embeddings
"""

import logging
import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set

import faiss
import numpy as np

from .models import StoredEntity, StoredChunk
from ..semantic.config import get_default_semantic_config

logger = logging.getLogger(__name__)


class FAISSManager:
    """FAISS indices with SemanticConfig thresholds"""
    
    def __init__(self, embedding_dim: int, storage_dir: Path):
        self.embedding_dim = embedding_dim
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.semantic_config = get_default_semantic_config()  # NEW: semantic config
        
        # Initialize FAISS indices (using Inner Product for normalized embeddings)
        self.entity_name_index = faiss.IndexFlatIP(embedding_dim)
        self.entity_context_index = faiss.IndexFlatIP(embedding_dim)
        self.chunk_index = faiss.IndexFlatIP(embedding_dim)
        
        # Mapping between entity/chunk IDs and FAISS indices
        self.entity_id_to_name_idx: Dict[str, int] = {}
        self.entity_id_to_context_idx: Dict[str, int] = {}
        self.chunk_id_to_idx: Dict[str, int] = {}
        
        # Reverse mappings for lookups
        self.name_idx_to_entity_id: Dict[int, str] = {}
        self.context_idx_to_entity_id: Dict[int, str] = {}
        self.chunk_idx_to_chunk_id: Dict[int, str] = {}
        
        # Track removed indices for cleanup
        self.removed_entity_indices: Set[int] = set()
        self.removed_chunk_indices: Set[int] = set()
        
        logger.info(f"📊 FAISS Manager initialized (dim: {embedding_dim})")
    
    def add_entity(self, entity: StoredEntity) -> bool:
        """Add entity embeddings to FAISS indices"""
        if entity.name_embedding is None or entity.context_embedding is None:
            logger.warning(f"⚠️ Entity {entity.id} missing embeddings, skipping FAISS add")
            return False
        
        try:
            # Add name embedding
            name_idx = self.entity_name_index.ntotal
            self.entity_name_index.add(entity.name_embedding.reshape(1, -1))
            
            # Add context embedding  
            context_idx = self.entity_context_index.ntotal
            self.entity_context_index.add(entity.context_embedding.reshape(1, -1))
            
            # Update mappings
            self.entity_id_to_name_idx[entity.id] = name_idx
            self.entity_id_to_context_idx[entity.id] = context_idx
            self.name_idx_to_entity_id[name_idx] = entity.id
            self.context_idx_to_entity_id[context_idx] = entity.id
            
            logger.debug(f"📊 Added entity {entity.id} to FAISS (name_idx: {name_idx}, context_idx: {context_idx})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add entity {entity.id} to FAISS: {e}")
            return False
    
    def add_chunk(self, chunk: StoredChunk) -> bool:
        """Add chunk embedding to FAISS index"""
        if chunk.text_embedding is None:
            logger.warning(f"⚠️ Chunk {chunk.id} missing embedding, skipping FAISS add")
            return False
        
        try:
            # Add chunk embedding
            chunk_idx = self.chunk_index.ntotal
            self.chunk_index.add(chunk.text_embedding.reshape(1, -1))
            
            # Update mappings
            self.chunk_id_to_idx[chunk.id] = chunk_idx
            self.chunk_idx_to_chunk_id[chunk_idx] = chunk.id
            
            logger.debug(f"📊 Added chunk {chunk.id} to FAISS (idx: {chunk_idx})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add chunk {chunk.id} to FAISS: {e}")
            return False
    
    def search_similar_entities_by_name(self, 
                                      query_embedding: np.ndarray,
                                      threshold: float = None,
                                      max_results: int = None) -> List[Tuple[str, float]]:
        """Search for similar entities by name using config defaults"""
        if threshold is None:
            threshold = self.semantic_config.name_search_threshold
        if max_results is None:
            max_results = self.semantic_config.name_search_max_results
            
        return self._search_entities(
            self.entity_name_index, 
            self.name_idx_to_entity_id,
            query_embedding, 
            threshold, 
            max_results
        )
    
    def search_similar_entities_by_context(self, 
                                         query_embedding: np.ndarray,
                                         threshold: float = None,
                                         max_results: int = None) -> List[Tuple[str, float]]:
        """Search for similar entities by context using config defaults"""
        if threshold is None:
            threshold = self.semantic_config.context_search_threshold
        if max_results is None:
            max_results = self.semantic_config.context_search_max_results
            
        return self._search_entities(
            self.entity_context_index,
            self.context_idx_to_entity_id,
            query_embedding,
            threshold,
            max_results
        )
    
    def search_similar_chunks(self,
                            query_embedding: np.ndarray,
                            threshold: float = 0.7,
                            max_results: int = 5) -> List[Tuple[str, float]]:
        """Search for similar chunks"""
        if self.chunk_index.ntotal == 0:
            return []
        
        try:
            # Search FAISS index
            k = min(max_results, self.chunk_index.ntotal)
            scores, indices = self.chunk_index.search(query_embedding.reshape(1, -1), k)
            
            # Convert to chunk IDs with filtering
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if score >= threshold and idx in self.chunk_idx_to_chunk_id:
                    chunk_id = self.chunk_idx_to_chunk_id[idx]
                    results.append((chunk_id, float(score)))
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Chunk search failed: {e}")
            return []
    
    def remove_entity(self, entity_id: str) -> bool:
        """Mark entity indices as removed"""
        try:
            # Mark indices as removed
            if entity_id in self.entity_id_to_name_idx:
                name_idx = self.entity_id_to_name_idx[entity_id]
                self.removed_entity_indices.add(name_idx)
                del self.entity_id_to_name_idx[entity_id]
                del self.name_idx_to_entity_id[name_idx]
            
            if entity_id in self.entity_id_to_context_idx:
                context_idx = self.entity_id_to_context_idx[entity_id]
                self.removed_entity_indices.add(context_idx)
                del self.entity_id_to_context_idx[entity_id]
                del self.context_idx_to_entity_id[context_idx]
            
            logger.debug(f"🗑️ Marked entity {entity_id} indices for removal")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to remove entity {entity_id}: {e}")
            return False
    
    def remove_chunk(self, chunk_id: str) -> bool:
        """Mark chunk index as removed"""
        try:
            if chunk_id in self.chunk_id_to_idx:
                chunk_idx = self.chunk_id_to_idx[chunk_id]
                self.removed_chunk_indices.add(chunk_idx)
                del self.chunk_id_to_idx[chunk_id]
                del self.chunk_idx_to_chunk_id[chunk_idx]
            
            logger.debug(f"🗑️ Marked chunk {chunk_id} index for removal")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to remove chunk {chunk_id}: {e}")
            return False
    
    def _search_entities(self,
                        index: faiss.Index,
                        idx_to_entity_id: Dict[int, str],
                        query_embedding: np.ndarray,
                        threshold: float,
                        max_results: int) -> List[Tuple[str, float]]:
        """Generic entity search implementation"""
        if index.ntotal == 0:
            return []
        
        try:
            # Search FAISS index
            k = min(max_results, index.ntotal)
            scores, indices = index.search(query_embedding.reshape(1, -1), k)
            
            # Convert to entity IDs with filtering
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if (score >= threshold and 
                    idx in idx_to_entity_id and 
                    idx not in self.removed_entity_indices):
                    entity_id = idx_to_entity_id[idx]
                    results.append((entity_id, float(score)))
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Entity search failed: {e}")
            return []
    
    def rebuild_indices_if_needed(self, entities: Dict[str, StoredEntity], 
                                chunks: Dict[str, StoredChunk]) -> bool:
        """Rebuild indices if too many removals have accumulated"""
        # Check if rebuild needed (>20% removals)
        name_removal_ratio = len(self.removed_entity_indices) / max(self.entity_name_index.ntotal, 1)
        chunk_removal_ratio = len(self.removed_chunk_indices) / max(self.chunk_index.ntotal, 1)
        
        if name_removal_ratio > 0.2 or chunk_removal_ratio > 0.2:
            logger.info(f"🔄 Rebuilding FAISS indices (removals: {name_removal_ratio:.1%} entities, {chunk_removal_ratio:.1%} chunks)")
            return self._rebuild_indices(entities, chunks)
        
        return False
    
    def _rebuild_indices(self, entities: Dict[str, StoredEntity], 
                        chunks: Dict[str, StoredChunk]) -> bool:
        """Rebuild all FAISS indices from scratch"""
        try:
            # Create new indices
            self.entity_name_index = faiss.IndexFlatIP(self.embedding_dim)
            self.entity_context_index = faiss.IndexFlatIP(self.embedding_dim)
            self.chunk_index = faiss.IndexFlatIP(self.embedding_dim)
            
            # Clear mappings
            self.entity_id_to_name_idx.clear()
            self.entity_id_to_context_idx.clear()
            self.chunk_id_to_idx.clear()
            self.name_idx_to_entity_id.clear()
            self.context_idx_to_entity_id.clear()
            self.chunk_idx_to_chunk_id.clear()
            self.removed_entity_indices.clear()
            self.removed_chunk_indices.clear()
            
            # Re-add all entities
            for entity in entities.values():
                self.add_entity(entity)
            
            # Re-add all chunks
            for chunk in chunks.values():
                self.add_chunk(chunk)
            
            logger.info(f"✅ FAISS indices rebuilt: {len(entities)} entities, {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to rebuild FAISS indices: {e}")
            return False
    
    def save_to_disk(self) -> bool:
        """Save FAISS indices and mappings to disk"""
        try:
            # Save FAISS indices
            faiss.write_index(self.entity_name_index, str(self.storage_dir / "entity_name.faiss"))
            faiss.write_index(self.entity_context_index, str(self.storage_dir / "entity_context.faiss"))
            faiss.write_index(self.chunk_index, str(self.storage_dir / "chunk.faiss"))
            
            # Save mappings
            mappings = {
                'entity_id_to_name_idx': self.entity_id_to_name_idx,
                'entity_id_to_context_idx': self.entity_id_to_context_idx,
                'chunk_id_to_idx': self.chunk_id_to_idx,
                'name_idx_to_entity_id': self.name_idx_to_entity_id,
                'context_idx_to_entity_id': self.context_idx_to_entity_id,
                'chunk_idx_to_chunk_id': self.chunk_idx_to_chunk_id,
                'removed_entity_indices': self.removed_entity_indices,
                'removed_chunk_indices': self.removed_chunk_indices
            }
            
            with open(self.storage_dir / "faiss_mappings.pkl", 'wb') as f:
                pickle.dump(mappings, f)
            
            logger.info(f"💾 FAISS indices saved to {self.storage_dir}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save FAISS indices: {e}")
            return False
    
    def load_from_disk(self) -> bool:
        """Load FAISS indices and mappings from disk"""
        try:
            # Check if files exist
            index_files = [
                self.storage_dir / "entity_name.faiss",
                self.storage_dir / "entity_context.faiss", 
                self.storage_dir / "chunk.faiss",
                self.storage_dir / "faiss_mappings.pkl"
            ]
            
            if not all(f.exists() for f in index_files):
                logger.info("📂 No existing FAISS indices found, starting fresh")
                return False
            
            # Load FAISS indices
            self.entity_name_index = faiss.read_index(str(self.storage_dir / "entity_name.faiss"))
            self.entity_context_index = faiss.read_index(str(self.storage_dir / "entity_context.faiss"))
            self.chunk_index = faiss.read_index(str(self.storage_dir / "chunk.faiss"))
            
            # Load mappings
            with open(self.storage_dir / "faiss_mappings.pkl", 'rb') as f:
                mappings = pickle.load(f)
            
            self.entity_id_to_name_idx = mappings.get('entity_id_to_name_idx', {})
            self.entity_id_to_context_idx = mappings.get('entity_id_to_context_idx', {})
            self.chunk_id_to_idx = mappings.get('chunk_id_to_idx', {})
            self.name_idx_to_entity_id = mappings.get('name_idx_to_entity_id', {})
            self.context_idx_to_entity_id = mappings.get('context_idx_to_entity_id', {})
            self.chunk_idx_to_chunk_id = mappings.get('chunk_idx_to_chunk_id', {})
            self.removed_entity_indices = mappings.get('removed_entity_indices', set())
            self.removed_chunk_indices = mappings.get('removed_chunk_indices', set())
            
            logger.info(f"📂 FAISS indices loaded: {self.entity_name_index.ntotal} entities, {self.chunk_index.ntotal} chunks")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load FAISS indices: {e}")
            return False
    
    def get_stats(self) -> Dict[str, int]:
        """Get FAISS statistics"""
        return {
            'entity_name_count': self.entity_name_index.ntotal,
            'entity_context_count': self.entity_context_index.ntotal,
            'chunk_count': self.chunk_index.ntotal,
            'removed_entities': len(self.removed_entity_indices),
            'removed_chunks': len(self.removed_chunk_indices),
            'embedding_dimension': self.embedding_dim
        }