"""
Entity merger for bulk merging of similar entity clusters
Handles canonical selection, alias merging, and relationship creation
"""

import logging
from typing import Dict, List, Set, Tuple, Optional
from ..models import StoredEntity, EntityRelationship, RelationType

logger = logging.getLogger(__name__)


class EntityMerger:
    """
    Handles bulk merging of entity clusters identified by Union-Find
    Creates canonical entities and manages merge relationships
    """
    
    def __init__(self):
        pass
    
    def merge_entity_cluster(self, cluster_entities: Dict[str, StoredEntity]) -> Tuple[str, StoredEntity, List[EntityRelationship]]:
        """
        Merge a cluster of similar entities into single canonical entity
        
        Args:
            cluster_entities: Dict of entity_id -> StoredEntity to merge
            
        Returns:
            (canonical_id, canonical_entity, merge_relationships)
        """
        if len(cluster_entities) == 1:
            # Single entity - no merge needed
            entity_id, entity = next(iter(cluster_entities.items()))
            return entity_id, entity, []
        
        # Select canonical entity
        canonical_id = self._select_canonical_entity(cluster_entities)
        canonical_entity = cluster_entities[canonical_id]
        
        # Merge data from all entities into canonical
        self._merge_entity_data(canonical_entity, cluster_entities)
        
        # Create merge relationships
        relationships = self._create_merge_relationships(canonical_id, cluster_entities)
        
        # Mark non-canonical entities as merged
        self._mark_entities_as_merged(canonical_id, cluster_entities)
        
        logger.info(f"Merged cluster of {len(cluster_entities)} entities into canonical: {canonical_entity.name}")
        
        return canonical_id, canonical_entity, relationships
    
    def bulk_merge_clusters(self, clusters: Dict[str, Set[str]], 
                          all_entities: Dict[str, StoredEntity]) -> Dict[str, Tuple[StoredEntity, List[EntityRelationship]]]:
        """
        Bulk merge multiple clusters
        
        Args:
            clusters: Dict of canonical_id -> set of entity_ids in cluster
            all_entities: All entities by ID
            
        Returns:
            Dict of canonical_id -> (merged_entity, relationships)
        """
        merge_results = {}
        
        for canonical_id, cluster_member_ids in clusters.items():
            if len(cluster_member_ids) <= 1:
                continue  # Skip single-entity clusters
            
            # Get cluster entities
            cluster_entities = {
                entity_id: all_entities[entity_id] 
                for entity_id in cluster_member_ids 
                if entity_id in all_entities
            }
            
            if len(cluster_entities) <= 1:
                continue
            
            # Merge cluster
            final_canonical_id, merged_entity, relationships = self.merge_entity_cluster(cluster_entities)
            merge_results[final_canonical_id] = (merged_entity, relationships)
        
        logger.info(f"Bulk merged {len(merge_results)} clusters")
        return merge_results
    
    def _select_canonical_entity(self, entities: Dict[str, StoredEntity]) -> str:
        """
        Select canonical entity based on:
        1. Most source chunks (stability)
        2. Highest confidence (quality)
        3. Longest description (completeness)
        """
        best_entity_id = None
        best_score = -1
        
        for entity_id, entity in entities.items():
            # Score components
            source_count = len(entity.source_chunk_ids)
            confidence = entity.confidence
            description_length = len(entity.description)
            
            # Weighted score: sources matter most, then confidence, then description
            score = (source_count * 10) + (confidence * 5) + (description_length * 0.01)
            
            if score > best_score:
                best_score = score
                best_entity_id = entity_id
        
        return best_entity_id
    
    def _merge_entity_data(self, canonical_entity: StoredEntity, all_entities: Dict[str, StoredEntity]):
        """Merge data from all entities into canonical entity"""
        
        # Collect all aliases
        all_aliases = set(canonical_entity.aliases)
        
        # Collect all source chunks and documents
        all_chunks = set(canonical_entity.source_chunk_ids)
        all_documents = set(canonical_entity.document_sources)
        
        # Best description (longest)
        best_description = canonical_entity.description
        best_context = canonical_entity.context
        
        # Highest confidence
        max_confidence = canonical_entity.confidence
        
        for entity_id, entity in all_entities.items():
            if entity_id == canonical_entity.id:
                continue
            
            # Add entity name as alias if different
            if entity.name.lower() != canonical_entity.name.lower():
                all_aliases.add(entity.name)
            
            # Add all aliases
            all_aliases.update(entity.aliases)
            
            # Add all source chunks and documents
            all_chunks.update(entity.source_chunk_ids)
            all_documents.update(entity.document_sources)
            
            # Keep best description
            if len(entity.description) > len(best_description):
                best_description = entity.description
            
            # Keep best context
            if len(entity.context) > len(best_context):
                best_context = entity.context
            
            # Keep highest confidence
            if entity.confidence > max_confidence:
                max_confidence = entity.confidence
        
        # Update canonical entity
        canonical_entity.aliases = list(all_aliases)
        canonical_entity.source_chunk_ids = list(all_chunks)
        canonical_entity.document_sources = list(all_documents)
        canonical_entity.description = best_description
        canonical_entity.context = best_context
        canonical_entity.confidence = max_confidence
        canonical_entity.merge_count = len(all_entities) - 1  # Number of entities merged into this one
        canonical_entity.update_timestamp()
    
    
    def _create_merge_relationships(self, canonical_id: str, 
                                  all_entities: Dict[str, StoredEntity]) -> List[EntityRelationship]:
        """Create MERGED_FROM and ALIAS_OF relationships"""
        relationships = []
        
        for entity_id, entity in all_entities.items():
            if entity_id == canonical_id:
                continue
            
            # MERGED_FROM relationship
            merge_relationship = EntityRelationship(
                source_id=canonical_id,
                target_id=entity_id,
                relation_type=RelationType.MERGED_FROM,
                confidence=1.0,
                evidence_text=f"Merged {entity.name} into {all_entities[canonical_id].name}",
                discovery_method="semantic_clustering"
            )
            relationships.append(merge_relationship)
            
            # ALIAS_OF relationship
            alias_relationship = EntityRelationship(
                source_id=canonical_id,
                target_id=entity_id,
                relation_type=RelationType.ALIAS_OF,
                confidence=1.0,
                evidence_text=f"{entity.name} is alias of {all_entities[canonical_id].name}",
                discovery_method="semantic_clustering"
            )
            relationships.append(alias_relationship)
        
        return relationships
    
    def _mark_entities_as_merged(self, canonical_id: str, all_entities: Dict[str, StoredEntity]):
        """Mark non-canonical entities as merged (add metadata)"""
        for entity_id, entity in all_entities.items():
            if entity_id == canonical_id:
                continue
            
            # Add merged metadata (we can't modify model structure, so use description)
            if not hasattr(entity, 'merged_into'):
                # Store merge info in context or description
                merge_info = f" [MERGED_INTO: {canonical_id}]"
                if merge_info not in entity.context:
                    entity.context += merge_info
    
    def get_merge_summary(self, merge_results: Dict[str, Tuple[StoredEntity, List[EntityRelationship]]]) -> Dict[str, any]:
        """Get summary statistics of merge operations"""
        total_relationships = sum(len(relationships) for _, relationships in merge_results.values())
        total_entities_merged = total_relationships  # Each relationship = one entity merged
        
        # Count by entity type
        type_counts = {}
        for canonical_entity, _ in merge_results.values():
            entity_type = canonical_entity.type
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
        
        return {
            'clusters_merged': len(merge_results),
            'total_entities_merged': total_entities_merged,
            'total_relationships_created': total_relationships,
            'merges_by_type': type_counts
        }