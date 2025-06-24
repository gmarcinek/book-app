"""
Weighted similarity calculations with entity_config
Multi-component similarity: separate name, description, context comparison
"""

from ..models import StoredEntity
from ner.entity_config import DeduplicationConfig


class WeightedSimilarity:
    """Weighted similarity with multi-component comparison"""
    
    def __init__(self):
        self._embedder = None  # Will be injected
    
    def set_embedder(self, embedder):
        """Inject embedder for multi-component similarity"""
        self._embedder = embedder
    
    def calculate_similarity(self, entity1: StoredEntity, entity2: StoredEntity, 
                           base_similarity: float) -> float:
        """Calculate multi-component weighted similarity"""
        if entity1.type != entity2.type:
            return 0.0  # Different types never match
        
        # Use multi-component similarity if embedder available
        if self._embedder:
            component_similarity = self._calculate_multi_component_similarity(entity1, entity2)
        else:
            # Fallback to base similarity
            component_similarity = base_similarity
        
        # Apply additional weights
        stability_weight = self._calculate_stability_weight(entity1, entity2)
        confidence_weight = self._calculate_confidence_weight(entity1, entity2)
        content_bonus = self._calculate_content_overlap(entity1, entity2)
        
        # Final weighted score
        weighted_score = component_similarity * stability_weight * confidence_weight + content_bonus
        
        return min(1.0, weighted_score)  # Cap at 1.0
    
    def _calculate_multi_component_similarity(self, entity1: StoredEntity, entity2: StoredEntity) -> float:
        """Calculate similarity by comparing name, description, context separately"""
        
        # Generate separate embeddings for each component
        name1_emb = self._embedder._get_cached_embedding(entity1.name, "component_name")
        name2_emb = self._embedder._get_cached_embedding(entity2.name, "component_name")
        
        desc1_emb = self._embedder._get_cached_embedding(entity1.description, "component_desc")
        desc2_emb = self._embedder._get_cached_embedding(entity2.description, "component_desc")
        
        context1_emb = self._embedder._get_cached_embedding(entity1.context, "component_context")
        context2_emb = self._embedder._get_cached_embedding(entity2.context, "component_context")
        
        # Calculate component similarities
        name_similarity = self._embedder.compute_similarity(name1_emb, name2_emb)
        desc_similarity = self._embedder.compute_similarity(desc1_emb, desc2_emb)
        context_similarity = self._embedder.compute_similarity(context1_emb, context2_emb)
        
        # Get type-specific weights from config
        weights = DeduplicationConfig.get_component_weights(entity1.type)
        
        # Weighted combination
        final_similarity = (
            name_similarity * weights["name"] +
            desc_similarity * weights["description"] + 
            context_similarity * weights["context"]
        )
        
        # Debug logging
        print(f"🧮 COMPONENT SIMILARITIES:")
        print(f"   🏷️ Name: {name_similarity:.3f} (weight: {weights['name']:.2f})")
        print(f"   📝 Description: {desc_similarity:.3f} (weight: {weights['description']:.2f})")
        print(f"   🌍 Context: {context_similarity:.3f} (weight: {weights['context']:.2f})")
        print(f"   ⚖️ Final: {final_similarity:.3f}")
        
        return final_similarity
    
    def should_merge(self, entity1: StoredEntity, entity2: StoredEntity, 
                    similarity_score: float) -> bool:
        """Determine if entities should be merged using type-specific threshold"""
        threshold = DeduplicationConfig.get_merge_threshold_for_type(entity1.type)
        return similarity_score >= threshold
    
    def _calculate_stability_weight(self, entity1: StoredEntity, entity2: StoredEntity) -> float:
        """Weight based on number of source chunks using centralized config"""
        config = DeduplicationConfig.get_stability_config()
        
        sources1 = len(entity1.source_chunk_ids)
        sources2 = len(entity2.source_chunk_ids)
        
        # More sources = more stable entity = higher weight
        min_sources = min(sources1, sources2)
        
        if max(sources1, sources2) == 0:
            return config["no_sources_weight"]
        
        # Diminishing returns using config values
        stability = config["single_source_weight"] + min(
            config["max_weight"] - config["single_source_weight"], 
            min_sources * config["increment_per_source"]
        )
        return min(config["max_weight"], stability)
    
    def _calculate_confidence_weight(self, entity1: StoredEntity, entity2: StoredEntity) -> float:
        """Weight based on entity confidence levels using centralized config"""
        config = DeduplicationConfig.get_confidence_config()
        
        avg_confidence = (entity1.confidence + entity2.confidence) / 2
        
        # Apply configured confidence scaling
        return config["base_weight"] + (avg_confidence * config["scale_factor"])
    
    def _calculate_content_overlap(self, entity1: StoredEntity, entity2: StoredEntity) -> float:
        """Bonus score for content word overlap using centralized config"""
        config = DeduplicationConfig.get_content_overlap_config()
        
        content1 = f"{entity1.name} {entity1.description} {entity1.context}".lower()
        content2 = f"{entity2.name} {entity2.description} {entity2.context}".lower()
        
        words1 = set(word for word in content1.split() if len(word) > config["min_word_length"])
        words2 = set(word for word in content2.split() if len(word) > config["min_word_length"])
        
        if not words1 or not words2:
            return 0.0
        
        overlap_ratio = len(words1 & words2) / len(words1 | words2)
        return min(config["max_bonus"], overlap_ratio * config["overlap_multiplier"])