"""
Entity batch clustering - extracted from EntityExtractor
Single responsibility: batch cluster entities per chunk
"""

import logging
from typing import List, Dict, Any
from .base import ExtractedEntity

logger = logging.getLogger(__name__)


class EntityBatchClusterer:
    """Handles batch clustering of entities per chunk"""
    
    def __init__(self, semantic_store, extraction_stats):
        self.semantic_store = semantic_store
        self.extraction_stats = extraction_stats
    
    def batch_cluster_chunk_entities(self, chunk_entities: List[ExtractedEntity], chunk_id: str) -> List[str]:
        """
        BATCH clustering: chunk entities vs database in single similarity matrix
        CORE OPTIMIZATION: replaces N² individual similarity calls
        """
        if not chunk_entities:
            return []
        
        entity_ids = []
        
        try:
            logger.debug(f"🔄 Batch clustering {len(chunk_entities)} entities from chunk")
            
            # Group entities by type for batch processing
            entities_by_type = {}
            for entity in chunk_entities:
                entity_type = entity.type
                if entity_type not in entities_by_type:
                    entities_by_type[entity_type] = []
                entities_by_type[entity_type].append(entity)
            
            # Process each type separately (same-type clustering only)
            for entity_type, type_entities in entities_by_type.items():
                type_entity_ids = self._batch_cluster_entities_by_type(type_entities, entity_type, chunk_id)
                entity_ids.extend(type_entity_ids)
            
            logger.debug(f"✅ Batch clustered to {len(set(entity_ids))} unique entities")
            return entity_ids
            
        except Exception as e:
            logger.error(f"❌ Batch clustering failed for chunk: {e}")
            return []
    
    def _batch_cluster_entities_by_type(self, type_entities: List[ExtractedEntity], entity_type: str, chunk_id: str) -> List[str]:
        """Batch cluster entities of same type using similarity matrix"""
        entity_ids = []
        
        # Get existing entities of same type from database
        existing_entities = {
            eid: entity for eid, entity in self.semantic_store.entities.items()
            if entity.type == entity_type
        }
        
        if not existing_entities:
            # No existing entities - create all as new
            for entity in type_entities:
                entity_id = self._create_new_entity(entity, chunk_id)
                entity_ids.append(entity_id)
            return entity_ids
        
        # BATCH similarity computation - CORE OPTIMIZATION
        for entity in type_entities:
            # Convert ExtractedEntity to StoredEntity format
            temp_entity = self._convert_to_stored_entity(entity)
            
            # Generate embeddings
            name_embedding, context_embedding = self.semantic_store.embedder.generate_entity_embeddings(temp_entity)
            temp_entity.name_embedding = name_embedding
            temp_entity.context_embedding = context_embedding
            
            # Find similar entities using batch engine
            similar_entities = self.semantic_store.similarity_engine.find_all_similar_entities(
                temp_entity, existing_entities, self.semantic_store.embedder
            )
            
            if similar_entities:
                # Merge with first similar entity (highest similarity)
                similar_id = similar_entities[0][0]
                self._merge_into_existing_entity(entity, similar_id, chunk_id)
                entity_ids.append(similar_id)
                self.extraction_stats["semantic_deduplication_hits"] += 1
            else:
                # Create new entity
                entity_id = self._create_new_entity(entity, chunk_id)
                entity_ids.append(entity_id)
                existing_entities[entity_id] = self.semantic_store.entities[entity_id]  # Add to local cache
        
        return entity_ids
    
    def _convert_to_stored_entity(self, extracted_entity: ExtractedEntity):
        """Convert ExtractedEntity to StoredEntity format"""
        from ..storage.models import StoredEntity
        
        return StoredEntity(
            id="temp",
            name=extracted_entity.name,
            type=extracted_entity.type,
            description=extracted_entity.description,
            confidence=extracted_entity.confidence,
            aliases=extracted_entity.aliases,
            context=extracted_entity.context
        )
    
    def _create_new_entity(self, entity: ExtractedEntity, chunk_id: str) -> str:
        """Create new entity bypassing add_entity_with_deduplication"""
        from ..storage.models import StoredEntity, create_entity_id
        
        # Create entity directly in semantic store
        entity_id = create_entity_id(entity.name, entity.type)
        
        stored_entity = StoredEntity(
            id=entity_id,
            name=entity.name,
            type=entity.type,
            description=entity.description,
            confidence=entity.confidence,
            aliases=entity.aliases,
            context=entity.context
        )
        
        # Add chunk reference
        stored_entity.add_source_chunk(chunk_id)
        stored_entity.add_document_source(
            self.semantic_store.chunks[chunk_id].document_source if chunk_id in self.semantic_store.chunks else "unknown"
        )
        
        # Generate embeddings
        name_embedding, context_embedding = self.semantic_store.embedder.generate_entity_embeddings(stored_entity)
        stored_entity.name_embedding = name_embedding
        stored_entity.context_embedding = context_embedding
        
        # Add to stores
        self.semantic_store.entities[entity_id] = stored_entity
        self.semantic_store.union_find.add_entity(entity_id)
        self.semantic_store.faiss_manager.add_entity(stored_entity)
        self.semantic_store.relationship_manager.add_entity_node(stored_entity)
        
        # Update ExtractedEntity
        entity.semantic_store_id = entity_id
        
        logger.info(f"✨ Created new entity: {entity.name} ({entity.type})")
        return entity_id
    
    def _merge_into_existing_entity(self, entity: ExtractedEntity, existing_entity_id: str, chunk_id: str):
        """Merge entity into existing entity"""
        existing_entity = self.semantic_store.entities[existing_entity_id]
        
        # Merge data
        if entity.confidence > existing_entity.confidence:
            existing_entity.confidence = entity.confidence
        
        if len(entity.description) > len(existing_entity.description):
            existing_entity.description = entity.description
        
        # Merge aliases
        new_aliases = set(entity.aliases)
        if entity.name != existing_entity.name:
            new_aliases.add(entity.name)
        
        discovered_aliases = existing_entity.merge_aliases(list(new_aliases))
        
        # Add chunk reference
        existing_entity.add_source_chunk(chunk_id)
        existing_entity.add_document_source(
            self.semantic_store.chunks[chunk_id].document_source if chunk_id in self.semantic_store.chunks else "unknown"
        )
        
        # Update ExtractedEntity
        entity.semantic_store_id = existing_entity_id
        if discovered_aliases:
            entity.aliases.extend(discovered_aliases)