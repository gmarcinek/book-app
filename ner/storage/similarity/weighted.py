"""
Weighted similarity calculations with SemanticConfig
Type-aware thresholds and multi-factor similarity scoring
"""

from typing import Dict, Tuple
import numpy as np
from ..models import StoredEntity
from ...semantic.config import get_default_semantic_config


class WeightedSimilarity:
    """Weighted similarity with SemanticConfig thresholds"""
    
    def __init__(self):
        self.semantic_config = get_default_semantic_config()  # NEW: semantic config
    
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
        """Get similarity threshold for given entity type using config"""
        return self.semantic_config.get_threshold_for_type(entity_type)
    
    def should_merge(self, entity1: StoredEntity, entity2: StoredEntity, 
                    similarity_score: float) -> bool:
        """Determine if entities should be merged using config threshold"""
        threshold = self.get_threshold_for_type(entity1.type)
        return similarity_score >= threshold
    
    def _get_type_weight(self, entity_type: str) -> float:
        """Weight factor based on entity type reliability"""
        weights = {
            # === SIMPLE DOMAIN (stare nazwy) ===
            'OSOBA': 1.2,        # Names are usually distinctive
            'ORGANIZACJA': 1.1,   # Organization names quite distinctive
            'MIEJSCE': 1.0,       # Places can be ambiguous
            'PRZEDMIOT': 0.9,     # Objects often have generic names
            'KONCEPCJA': 0.8,     # Concepts are often similar
            
            # === LITERARY DOMAIN (nowe nazwy) - KONSERWATYWNE WAGI ===
            'CHARACTER': 1.2,     # Wysoka waga - imiona są bardzo distinctive  
            'LOCATION': 1.2,      # Wysoka waga - nazwy lokacji mają być różne
            'OBJECT': 1.1,        # Wysoka waga - obiekty powinny być distinctive
            'EMOTIONAL_STATE': 0.8,  # Stany emocjonalne często podobne
            'EVENT': 0.9,        # Wydarzenia umiarkowanie distinctive
            'DIALOG': 0.7,       # Dialogi często się nakładają
            
            'default': 1.0
        }
        return weights.get(entity_type, weights['default'])
    
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
        """Bonus score for content word overlap using config max bonus"""
        content1 = f"{entity1.name} {entity1.description} {entity1.context}".lower()
        content2 = f"{entity2.name} {entity2.description} {entity2.context}".lower()
        
        words1 = set(word for word in content1.split() if len(word) > 2)
        words2 = set(word for word in content2.split() if len(word) > 2)
        
        if not words1 or not words2:
            return 0.0
        
        overlap_ratio = len(words1 & words2) / len(words1 | words2)
        
        # Use config max bonus instead of hardcoded 0.1
        max_bonus = self.semantic_config.max_content_overlap_bonus
        return min(max_bonus, overlap_ratio * 0.4)