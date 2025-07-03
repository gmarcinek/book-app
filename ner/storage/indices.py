# ner/storage/indices.py
"""
FAISS indices management with OpenAI embeddings (1536 dimensions)
"""

import logging
import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set

import faiss
import numpy as np

from .models import StoredEntity, StoredChunk

logger = logging.getLogger(__name__)

# Simple search thresholds - no complex deduplication logic
DEFAULT_CONTEXT_SEARCH_THRESHOLD = 0.6
DEFAULT_MAX_SEARCH_RESULTS = 10


class FAISSManager:
    """FAISS indices for OpenAI embeddings (1536 dimensions) - search only"""
    
    def __init__(self, embedding_dim: int, storage_dir: Path):
        # Initialize FAISS manager with OpenAI embedding dimensions
        if embedding_dim != 1536:
            logger.warning(f"⚠️ Expected 1536 dimensions for OpenAI embeddings, got {embedding_dim}")
        
        self.embedding_dim = embedding_dim
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize FAISS indices (Inner Product for normalized embeddings)
        self.entity_name_index = faiss.IndexFlatIP(embedding_dim)
        self.entity_context_index = faiss.IndexFlatIP(embedding_dim)
        self.chunk_index = faiss.IndexFlatIP(embedding_dim)
        
        # ID mappings
        self.entity_id_to_name_idx: Dict[str, int] = {}
        self.entity_id_to_context_idx: Dict[str, int] = {}
        self.chunk_id_to_idx: Dict[str, int] = {}
        
        # Reverse mappings
        self.name_idx_to_entity_id: Dict[int, str] = {}
        self.context_idx_to_entity_id: Dict[int, str] = {}
        self.chunk_idx_to_chunk_id: Dict[int, str] = {}
        
        # Removed indices tracking
        self.removed_entity_indices: Set[int] = set()
        self.removed_chunk_indices: Set[int] = set()
        
        print(f"📊 FAISS Manager initialized ({embedding_dim}D)")
        logger.info(f"📊 FAISS Manager initialized (dim: {embedding_dim})")
    
    def add_entity(self, entity: StoredEntity) -> bool:
        """Add entity embeddings to FAISS indices"""
        if entity.name_embedding is None or entity.context_embedding is None:
            print(f"⚠️ Entity {entity.id} missing embeddings, skipping FAISS add")
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
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to add entity {entity.id} to FAISS: {e}")
            return False
    
    def add_chunk(self, chunk: StoredChunk) -> bool:
        """Add chunk embedding to FAISS index"""
        if chunk.text_embedding is None:
            print(f"⚠️ Chunk {chunk.id} missing embedding, skipping FAISS add")
            return False
        
        try:
            chunk_idx = self.chunk_index.ntotal
            self.chunk_index.add(chunk.text_embedding.reshape(1, -1))
            
            self.chunk_id_to_idx[chunk.id] = chunk_idx
            self.chunk_idx_to_chunk_id[chunk_idx] = chunk.id
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to add chunk {chunk.id} to FAISS: {e}")
            return False

    
    def search_similar_entities_by_context(self, 
                                         query_embedding: np.ndarray,
                                         threshold: float = None,
                                         max_results: int = None) -> List[Tuple[str, float]]:
        """Search entities by context embedding"""
        if threshold is None:
            threshold = DEFAULT_CONTEXT_SEARCH_THRESHOLD
        if max_results is None:
            max_results = DEFAULT_MAX_SEARCH_RESULTS
            
        return self._search_entities(
            self.entity_context_index,
            self.context_idx_to_entity_id, 
            query_embedding,
            threshold,
            max_results
        )
    
    def search_similar_chunks(self,
                            query_embedding: np.ndarray,
                            threshold: float = 0.6,
                            max_results: int = 20) -> List[Tuple[str, float]]:
        """Search chunks by text embedding"""
        if self.chunk_index.ntotal == 0:
            return []
        
        try:
            k = min(max_results, self.chunk_index.ntotal)
            scores, indices = self.chunk_index.search(query_embedding.reshape(1, -1), k)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if (score >= threshold and 
                    idx in self.chunk_idx_to_chunk_id and 
                    idx not in self.removed_chunk_indices):
                    chunk_id = self.chunk_idx_to_chunk_id[idx]
                    results.append((chunk_id, float(score)))
            
            return results
            
        except Exception as e:
            print(f"❌ Chunk search failed: {e}")
            return []
    
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
            k = min(max_results, index.ntotal)
            scores, indices = index.search(query_embedding.reshape(1, -1), k)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if (score >= threshold and 
                    idx in idx_to_entity_id and 
                    idx not in self.removed_entity_indices):
                    entity_id = idx_to_entity_id[idx]
                    results.append((entity_id, float(score)))
            
            return results
            
        except Exception as e:
            print(f"❌ Entity search failed: {e}")
            return []
    
    def save_to_disk(self):
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
            
            print(f"💾 FAISS indices saved")
            
        except Exception as e:
            print(f"❌ Failed to save FAISS indices: {e}")
    
    def load_from_disk(self) -> bool:
        """Load FAISS indices and mappings from disk"""
        try:
            index_files = [
                self.storage_dir / "entity_name.faiss",
                self.storage_dir / "entity_context.faiss", 
                self.storage_dir / "chunk.faiss",
                self.storage_dir / "faiss_mappings.pkl"
            ]
            
            if not all(f.exists() for f in index_files):
                print("📂 No existing FAISS indices found, starting fresh")
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
            
            print(f"📂 FAISS indices loaded: {self.entity_name_index.ntotal} entities, {self.chunk_index.ntotal} chunks")
            return True
            
        except Exception as e:
            print(f"❌ Failed to load FAISS indices: {e}")
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