"""
Weighted similarity calculations with entity_config
Type-aware thresholds and multi-factor similarity scoring
"""

from ..models import StoredEntity
from ner.entity_config import DeduplicationConfig


class WeightedSimilarity:
    """Weighted similarity with centralized config from entity_config"""
    
    def __init__(self):
        # No need to store semantic_config - use DeduplicationConfig directly
        pass
    
    def calculate_similarity(self, entity1: StoredEntity, entity2: StoredEntity, 
                           base_similarity: float) -> float:
        """Calculate weighted similarity between two entities"""
        if entity1.type != entity2.type:
            return 0.0  # Different types never match
        
        # Type weight factor
        type_weight = self._get_type_weight(entity1.type)
        
        # Stability weight (more sources = more reliable)
        stability_weight = self._calculate_stability_weight(entity1, entity2)
        
        # Confidence weight
        confidence_weight = self._calculate_confidence_weight(entity1, entity2)
        
        # Content overlap bonus using config
        content_bonus = self._calculate_content_overlap(entity1, entity2)
        
        # Final weighted score
        weighted_score = (
            base_similarity * type_weight * stability_weight * confidence_weight + content_bonus
        )
        
        return min(1.0, weighted_score)  # Cap at 1.0
    
    def get_threshold_for_type(self, entity_type: str) -> float:
        """Get similarity threshold for given entity type using centralized config"""
        return DeduplicationConfig.get_threshold_for_entity_type_string(entity_type)
    
    def should_merge(self, entity1: StoredEntity, entity2: StoredEntity, 
                    similarity_score: float) -> bool:
        """Determine if entities should be merged using centralized threshold"""
        threshold = self.get_threshold_for_type(entity1.type)
        return similarity_score >= threshold
    
    def _get_type_weight(self, entity_type: str) -> float:
        """Weight factor based on entity type reliability - uses centralized config"""
        return DeduplicationConfig.get_type_weight(entity_type)
    
    def _calculate_stability_weight(self, entity1: StoredEntity, entity2: StoredEntity) -> float:
        """Weight based on number of source chunks (stability indicator)"""
        sources1 = len(entity1.source_chunk_ids)
        sources2 = len(entity2.source_chunk_ids)
        
        # More sources = more stable entity = higher weight
        min_sources = min(sources1, sources2)
        max_sources = max(sources1, sources2)
        
        if max_sources == 0:
            return 0.8  # No sources is suspicious
        
        # Diminishing returns: 1 source = 0.9, 2 = 0.95, 3+ = 1.0
        stability = 0.9 + min(0.1, min_sources * 0.05)
        return stability
    
    def _calculate_confidence_weight(self, entity1: StoredEntity, entity2: StoredEntity) -> float:
        """Weight based on entity confidence levels"""
        avg_confidence = (entity1.confidence + entity2.confidence) / 2
        
        # Higher confidence = higher weight, but not too extreme
        return 0.8 + (avg_confidence * 0.2)  # Range: 0.8 - 1.0
    
    def _calculate_content_overlap(self, entity1: StoredEntity, entity2: StoredEntity) -> float:
        """Bonus score for content word overlap using centralized config"""
        content1 = f"{entity1.name} {entity1.description} {entity1.context}".lower()
        content2 = f"{entity2.name} {entity2.description} {entity2.context}".lower()
        
        words1 = set(word for word in content1.split() if len(word) > 2)
        words2 = set(word for word in content2.split() if len(word) > 2)
        
        if not words1 or not words2:
            return 0.0
        
        overlap_ratio = len(words1 & words2) / len(words1 | words2)
        
        # Use centralized config instead of hardcoded value
        max_bonus = DeduplicationConfig.MAX_CONTENT_OVERLAP_BONUS
        return min(max_bonus, overlap_ratio * 0.4)