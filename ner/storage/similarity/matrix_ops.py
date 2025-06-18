"""
Matrix operations for batch similarity computations
Efficient processing of multiple entity comparisons
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class MatrixOperations:
    """
    Batch matrix operations for entity similarity computations
    Replaces N² individual FAISS calls with efficient matrix operations
    """
    
    def __init__(self):
        pass
    
    def compute_similarity_matrix(self, embeddings1: np.ndarray, 
                                embeddings2: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Compute cosine similarity matrix between two sets of embeddings
        
        Args:
            embeddings1: Shape (n, dim) - first set of embeddings
            embeddings2: Shape (m, dim) - second set (if None, use embeddings1)
            
        Returns:
            Similarity matrix shape (n, m) with cosine similarities
        """
        if embeddings2 is None:
            embeddings2 = embeddings1
        
        # Normalize embeddings
        norm1 = np.linalg.norm(embeddings1, axis=1, keepdims=True)
        norm2 = np.linalg.norm(embeddings2, axis=1, keepdims=True)
        
        # Avoid division by zero
        norm1 = np.where(norm1 == 0, 1, norm1)
        norm2 = np.where(norm2 == 0, 1, norm2)
        
        normalized1 = embeddings1 / norm1
        normalized2 = embeddings2 / norm2
        
        # Compute cosine similarity matrix
        similarity_matrix = np.dot(normalized1, normalized2.T)
        
        # Clamp to valid range
        similarity_matrix = np.clip(similarity_matrix, 0.0, 1.0)
        
        return similarity_matrix
    
    def find_similar_pairs(self, similarity_matrix: np.ndarray, 
                          threshold: float, 
                          entity_ids1: List[str],
                          entity_ids2: Optional[List[str]] = None) -> List[Tuple[str, str, float]]:
        """
        Find entity pairs above similarity threshold from matrix
        
        Args:
            similarity_matrix: Precomputed similarity matrix
            threshold: Minimum similarity threshold
            entity_ids1: Entity IDs for rows
            entity_ids2: Entity IDs for columns (if None, use entity_ids1)
            
        Returns:
            List of (entity1_id, entity2_id, similarity) tuples
        """
        if entity_ids2 is None:
            entity_ids2 = entity_ids1
            # For self-similarity, ignore diagonal
            np.fill_diagonal(similarity_matrix, 0.0)
        
        # Find indices where similarity > threshold
        row_indices, col_indices = np.where(similarity_matrix >= threshold)
        
        similar_pairs = []
        for row_idx, col_idx in zip(row_indices, col_indices):
            similarity = similarity_matrix[row_idx, col_idx]
            entity1_id = entity_ids1[row_idx]
            entity2_id = entity_ids2[col_idx]
            
            # Avoid self-pairs and duplicates (for symmetric matrices)
            if entity1_id != entity2_id:
                similar_pairs.append((entity1_id, entity2_id, float(similarity)))
        
        # Sort by similarity (descending)
        similar_pairs.sort(key=lambda x: x[2], reverse=True)
        
        return similar_pairs
    
    def compute_cooccurrence_matrix(self, entity_chunk_mapping: Dict[str, List[str]]) -> Tuple[np.ndarray, List[str]]:
        """
        Compute co-occurrence matrix for entities based on shared chunks
        
        Args:
            entity_chunk_mapping: entity_id -> list of chunk_ids
            
        Returns:
            (cooccurrence_matrix, entity_ids_list)
        """
        entity_ids = list(entity_chunk_mapping.keys())
        n_entities = len(entity_ids)
        
        if n_entities == 0:
            return np.array([]), []
        
        # Create binary matrix: entity x chunk
        all_chunks = set()
        for chunks in entity_chunk_mapping.values():
            all_chunks.update(chunks)
        
        chunk_to_idx = {chunk_id: idx for idx, chunk_id in enumerate(sorted(all_chunks))}
        n_chunks = len(all_chunks)
        
        # Entity-chunk matrix
        entity_chunk_matrix = np.zeros((n_entities, n_chunks), dtype=bool)
        
        for entity_idx, entity_id in enumerate(entity_ids):
            for chunk_id in entity_chunk_mapping[entity_id]:
                chunk_idx = chunk_to_idx[chunk_id]
                entity_chunk_matrix[entity_idx, chunk_idx] = True
        
        # Co-occurrence matrix = entity_chunk_matrix @ entity_chunk_matrix.T
        cooccurrence_matrix = entity_chunk_matrix @ entity_chunk_matrix.T
        
        # Convert to float and normalize by total chunks per entity pair
        cooccurrence_matrix = cooccurrence_matrix.astype(float)
        
        return cooccurrence_matrix, entity_ids
    
    def batch_embedding_similarity(self, new_embeddings: np.ndarray,
                                 existing_embeddings: np.ndarray,
                                 new_entity_ids: List[str],
                                 existing_entity_ids: List[str],
                                 threshold: float) -> Dict[str, List[Tuple[str, float]]]:
        """
        Batch compute similarities between new and existing entities
        
        Args:
            new_embeddings: Embeddings for new entities (n, dim)
            existing_embeddings: Embeddings for existing entities (m, dim)
            new_entity_ids: IDs for new entities
            existing_entity_ids: IDs for existing entities
            threshold: Similarity threshold
            
        Returns:
            Dict mapping new_entity_id -> list of (existing_entity_id, similarity)
        """
        if len(new_entity_ids) == 0 or len(existing_entity_ids) == 0:
            return {}
        
        # Compute similarity matrix
        similarity_matrix = self.compute_similarity_matrix(new_embeddings, existing_embeddings)
        
        # Find similar pairs
        similar_pairs = self.find_similar_pairs(
            similarity_matrix, threshold, new_entity_ids, existing_entity_ids
        )
        
        # Group by new entity
        result = {entity_id: [] for entity_id in new_entity_ids}
        
        for new_id, existing_id, similarity in similar_pairs:
            result[new_id].append((existing_id, similarity))
        
        return result
    
    def get_top_k_similar(self, similarity_matrix: np.ndarray,
                         entity_ids1: List[str],
                         entity_ids2: List[str],
                         k: int = 5) -> Dict[str, List[Tuple[str, float]]]:
        """
        Get top-k most similar entities for each entity
        
        Returns:
            Dict mapping entity_id -> list of (similar_entity_id, similarity)
        """
        result = {}
        
        for i, entity_id in enumerate(entity_ids1):
            # Get similarities for this entity
            similarities = similarity_matrix[i, :]
            
            # Get top-k indices (excluding self if same lists)
            if entity_ids1 == entity_ids2:
                similarities[i] = -1  # Exclude self
            
            top_k_indices = np.argpartition(similarities, -k)[-k:]
            top_k_indices = top_k_indices[np.argsort(similarities[top_k_indices])][::-1]
            
            # Filter out low similarities and build result
            top_similar = []
            for idx in top_k_indices:
                similarity = similarities[idx]
                if similarity > 0:  # Exclude self and negatives
                    similar_entity_id = entity_ids2[idx]
                    top_similar.append((similar_entity_id, float(similarity)))
            
            result[entity_id] = top_similar
        
        return result