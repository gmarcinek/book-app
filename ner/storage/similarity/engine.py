"""
Main similarity engine coordinating weighted similarity and matrix operations
Central hub for all entity similarity computations
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

from .weighted import WeightedSimilarity
from .matrix_ops import MatrixOperations
from ..models import StoredEntity

logger = logging.getLogger(__name__)


class EntitySimilarityEngine:
    """
    Main similarity engine coordinating all similarity computations
    Combines weighted similarity with efficient matrix operations
    """
    
    def __init__(self):
        self.weighted_sim = WeightedSimilarity()
        self.matrix_ops = MatrixOperations()
    
    def find_all_similar_entities(self, new_entity: StoredEntity,
                                existing_entities: Dict[str, StoredEntity],
                                embedder) -> List[Tuple[str, float]]:
        """
        Find ALL similar entities to new entity (not just first match)
        
        Args:
            new_entity: Entity to find matches for
            existing_entities: Pool of existing entities to search
            embedder: EntityEmbedder instance for generating embeddings
            
        Returns:
            List of (entity_id, weighted_similarity) tuples, sorted by similarity
        """
        if not existing_entities:
            return []
        
        # Filter by same type first
        same_type_entities = {
            eid: entity for eid, entity in existing_entities.items()
            if entity.type == new_entity.type
        }
        
        if not same_type_entities:
            return []
        
        # Get embeddings for batch processing
        new_embedding = new_entity.context_embedding
        if new_embedding is None:
            logger.warning(f"No embedding for new entity {new_entity.name}")
            return []
        
        existing_embeddings = []
        existing_ids = []
        
        for entity_id, entity in same_type_entities.items():
            if entity.context_embedding is not None:
                existing_embeddings.append(entity.context_embedding)
                existing_ids.append(entity_id)
        
        if not existing_embeddings:
            return []
        
        # Convert to numpy arrays
        new_embeddings = new_embedding.reshape(1, -1)
        existing_embeddings = np.array(existing_embeddings)
        
        # Base threshold for initial filtering
        base_threshold = 0.3  # Lower threshold to catch more candidates
        
        # Batch similarity computation
        similar_candidates = self.matrix_ops.batch_embedding_similarity(
            new_embeddings, existing_embeddings,
            [new_entity.id], existing_ids,
            base_threshold
        )
        
        candidates = similar_candidates.get(new_entity.id, [])
        
        # Apply weighted similarity to all candidates
        weighted_results = []
        for existing_id, base_similarity in candidates:
            existing_entity = same_type_entities[existing_id]
            
            weighted_score = self.weighted_sim.calculate_similarity(
                new_entity, existing_entity, base_similarity
            )
            
            # Final threshold check with type-specific threshold
            if self.weighted_sim.should_merge(new_entity, existing_entity, weighted_score):
                weighted_results.append((existing_id, weighted_score))
        
        # Sort by weighted similarity (descending)
        weighted_results.sort(key=lambda x: x[1], reverse=True)
        
        logger.debug(f"Found {len(weighted_results)} similar entities for {new_entity.name}")
        return weighted_results
    
    def batch_find_similar_clusters(self, entities: Dict[str, StoredEntity],
                                  embedder) -> Dict[str, List[Tuple[str, float]]]:
        """
        Batch process to find similarity clusters among all entities
        More efficient than pairwise comparisons
        
        Returns:
            Dict mapping entity_id -> list of (similar_entity_id, similarity)
        """
        if len(entities) < 2:
            return {}
        
        # Group entities by type for efficient processing
        entities_by_type = {}
        for entity_id, entity in entities.items():
            entity_type = entity.type
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = {}
            entities_by_type[entity_type][entity_id] = entity
        
        all_similarities = {}
        
        # Process each type separately
        for entity_type, type_entities in entities_by_type.items():
            if len(type_entities) < 2:
                continue
            
            type_similarities = self._process_type_similarities(type_entities, entity_type)
            all_similarities.update(type_similarities)
        
        return all_similarities
    
    def compute_cooccurrence_similarities(self, entities: Dict[str, StoredEntity]) -> Dict[str, List[Tuple[str, float]]]:
        """
        Find entity similarities based on co-occurrence in same chunks
        Complements embedding-based similarity
        """
        # Build entity -> chunks mapping
        entity_chunk_mapping = {}
        for entity_id, entity in entities.items():
            entity_chunk_mapping[entity_id] = entity.source_chunk_ids
        
        # Compute co-occurrence matrix
        cooccurrence_matrix, entity_ids = self.matrix_ops.compute_cooccurrence_matrix(
            entity_chunk_mapping
        )
        
        if len(entity_ids) == 0:
            return {}
        
        # Convert co-occurrence counts to similarities
        # Normalize by total chunks per entity pair
        similarity_matrix = np.zeros_like(cooccurrence_matrix, dtype=float)
        
        for i in range(len(entity_ids)):
            for j in range(len(entity_ids)):
                if i != j:
                    shared_chunks = cooccurrence_matrix[i, j]
                    total_chunks = (cooccurrence_matrix[i, i] + 
                                  cooccurrence_matrix[j, j] - shared_chunks)
                    
                    if total_chunks > 0:
                        similarity_matrix[i, j] = shared_chunks / total_chunks
        
        # Find significant co-occurrences (threshold 0.2 = 20% shared chunks)
        cooccurrence_threshold = 0.2
        similar_pairs = self.matrix_ops.find_similar_pairs(
            similarity_matrix, cooccurrence_threshold, entity_ids
        )
        
        # Group by entity
        result = {entity_id: [] for entity_id in entity_ids}
        for entity1_id, entity2_id, similarity in similar_pairs:
            result[entity1_id].append((entity2_id, similarity))
        
        return result
    
    def _process_type_similarities(self, type_entities: Dict[str, StoredEntity],
                                 entity_type: str) -> Dict[str, List[Tuple[str, float]]]:
        """Process similarities within single entity type"""
        entity_ids = list(type_entities.keys())
        embeddings = []
        
        # Collect embeddings
        for entity_id in entity_ids:
            entity = type_entities[entity_id]
            if entity.context_embedding is not None:
                embeddings.append(entity.context_embedding)
            else:
                embeddings.append(np.zeros(384))  # Fallback zero embedding
        
        if not embeddings:
            return {}
        
        embeddings = np.array(embeddings)
        
        # Compute similarity matrix
        similarity_matrix = self.matrix_ops.compute_similarity_matrix(embeddings)
        
        # Get type-specific threshold
        base_threshold = self.weighted_sim.get_threshold_for_type(entity_type) - 0.1  # Lower for initial filtering
        
        # Find similar pairs
        similar_pairs = self.matrix_ops.find_similar_pairs(
            similarity_matrix, base_threshold, entity_ids
        )
        
        # Apply weighted similarity
        weighted_results = {}
        for entity_id in entity_ids:
            weighted_results[entity_id] = []
        
        for entity1_id, entity2_id, base_similarity in similar_pairs:
            entity1 = type_entities[entity1_id]
            entity2 = type_entities[entity2_id]
            
            weighted_score = self.weighted_sim.calculate_similarity(
                entity1, entity2, base_similarity
            )
            
            if self.weighted_sim.should_merge(entity1, entity2, weighted_score):
                weighted_results[entity1_id].append((entity2_id, weighted_score))
                weighted_results[entity2_id].append((entity1_id, weighted_score))
        
        # Sort each entity's similar entities by score
        for entity_id in weighted_results:
            weighted_results[entity_id].sort(key=lambda x: x[1], reverse=True)
        
        return weighted_results
    
    def get_similarity_stats(self, entities: Dict[str, StoredEntity]) -> Dict[str, int]:
        """Get statistics about similarity computations"""
        type_counts = {}
        for entity in entities.values():
            entity_type = entity.type
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
        
        return {
            'total_entities': len(entities),
            'entity_types': len(type_counts),
            'type_distribution': type_counts
        }