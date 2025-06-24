"""
Entity batch clustering - extracted from EntityExtractor
Single responsibility: batch cluster entities per chunk
OPTIMIZED: Single similarity matrix per chunk vs database
"""

import logging
from typing import List, Dict, Any
from .base import ExtractedEntity
from ner.entity_config import DeduplicationConfig

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
        """Batch cluster entities of same type using single similarity matrix"""
        entity_ids = []
        
        print(f"🔍🔍🔍🔍🔍🔍🔍🔍🔍 BATCH CLUSTER: Processing {len(type_entities)} entities of type {entity_type}")
        
        # Get existing entities of same type from database
        existing_entities = {
            eid: entity for eid, entity in self.semantic_store.entities.items()
            if entity.type == entity_type
        }
        
        print(f"🔍🔍🔍-------🔍🔍🔍 BATCH CLUSTER: Found {len(existing_entities)} existing entities of same type")
        
        if not existing_entities:
            # No existing entities - create all as new
            for entity in type_entities:
                entity_id = self._create_new_entity(entity, chunk_id)
                entity_ids.append(entity_id)
            return entity_ids
        
        # CORE OPTIMIZATION: Single similarity matrix for all chunk entities vs database
        chunk_entities_data = []
        for entity in type_entities:
            temp_entity = self._convert_to_stored_entity(entity)
            name_embedding, context_embedding = self.semantic_store.embedder.generate_entity_embeddings(temp_entity)
            temp_entity.name_embedding = name_embedding
            temp_entity.context_embedding = context_embedding
            chunk_entities_data.append((entity, temp_entity))
        
        # Batch similarity computation
        merge_decisions = self._compute_bulk_similarity(chunk_entities_data, existing_entities)
        
        # Process merge decisions
        for i, (extracted_entity, temp_entity) in enumerate(chunk_entities_data):
            similar_id = merge_decisions.get(i)
            
            if similar_id:
                self._merge_into_existing_entity(extracted_entity, similar_id, chunk_id)
                entity_ids.append(similar_id)
                self.extraction_stats["semantic_deduplication_hits"] += 1
            else:
                entity_id = self._create_new_entity(extracted_entity, chunk_id)
                entity_ids.append(entity_id)
                existing_entities[entity_id] = self.semantic_store.entities[entity_id]
        
        return entity_ids
    
    def _compute_bulk_similarity(self, chunk_entities_data: List, existing_entities: Dict) -> Dict[int, str]:
        """Compute similarity matrix for all chunk entities vs database entities"""
        if not chunk_entities_data or not existing_entities:
            return {}
        
        # Prepare embeddings matrices
        chunk_embeddings = []
        chunk_entity_ids = []
        chunk_idx_to_original = {}  # map string ID back to original index
        
        for i, item in enumerate(chunk_entities_data):
            if not isinstance(item, tuple) or len(item) != 2:
                continue
                
            extracted_entity, temp_entity = item
            
            if hasattr(temp_entity, 'context_embedding') and temp_entity.context_embedding is not None:
                chunk_embeddings.append(temp_entity.context_embedding)
                chunk_str_id = f"chunk_{i}"
                chunk_entity_ids.append(chunk_str_id)
                chunk_idx_to_original[chunk_str_id] = i
        
        existing_embeddings = []
        existing_entity_ids = []
        
        for entity_id, entity in existing_entities.items():
            if entity.context_embedding is not None:
                existing_embeddings.append(entity.context_embedding)
                existing_entity_ids.append(entity_id)
        
        if not chunk_embeddings or not existing_embeddings:
            return {}
        
        logger.info(f"🔄 BATCH: Computing similarity matrix {len(chunk_embeddings)}x{len(existing_embeddings)} instead of {len(chunk_entities_data)} individual calls")
        
        # Single similarity matrix computation
        import numpy as np
        chunk_embeddings = np.array(chunk_embeddings)
        existing_embeddings = np.array(existing_embeddings)
        
        # Use centralized config threshold instead of hardcoded
        similar_candidates = self.semantic_store.similarity_engine.matrix_ops.batch_embedding_similarity(
            chunk_embeddings, existing_embeddings,
            chunk_entity_ids, existing_entity_ids,
            DeduplicationConfig.BASE_SIMILARITY_THRESHOLD
        )
        
        # Apply weighted similarity and return merge decisions
        merge_decisions = {}
        for chunk_str_id, candidates in similar_candidates.items():
            if not candidates:
                continue
                
            chunk_idx = chunk_idx_to_original[chunk_str_id]
            extracted_entity, temp_entity = chunk_entities_data[chunk_idx]
            
            print(f"🔍 SIMILARITY: Entity '{temp_entity.name}' has {len(candidates)} candidates")
            
            best_match = None
            best_score = 0
            
            for existing_id, base_similarity in candidates:
                existing_entity = existing_entities[existing_id]
                
                # Enhanced debugging - show what's being compared
                debug_config = DeduplicationConfig.get_debug_config()
                
                print(f"🔍 ENTITY1: '{temp_entity.name}' ({temp_entity.type})")
                print(f"   📝 Description: {temp_entity.description[:debug_config['max_description_length']]}...")
                print(f"   🏷️ Aliases: {temp_entity.aliases}")
                print(f"   📊 Confidence: {temp_entity.confidence:.3f}")
                
                print(f"🔍 ENTITY2: '{existing_entity.name}' ({existing_entity.type})")
                print(f"   📝 Description: {existing_entity.description[:debug_config['max_description_length']]}...")
                print(f"   🏷️ Aliases: {existing_entity.aliases}")
                print(f"   📊 Confidence: {existing_entity.confidence:.3f}")
                
                # Show semantic text used for embeddings
                if debug_config['show_semantic_text']:
                    semantic_text1 = temp_entity.get_semantic_text_for_context()
                    semantic_text2 = existing_entity.get_semantic_text_for_context()
                    print(f"🧠 SEMANTIC_TEXT1: {semantic_text1[:100]}...")
                    print(f"🧠 SEMANTIC_TEXT2: {semantic_text2[:100]}...")
                
                weighted_score = self.semantic_store.similarity_engine.weighted_sim.calculate_similarity(
                    temp_entity, existing_entity, base_similarity
                )
                
                print(f"🔍 SIMILARITY: '{temp_entity.name}' vs '{existing_entity.name}' = {weighted_score:.3f} (base: {base_similarity:.3f})")
                
                should_merge = self.semantic_store.similarity_engine.weighted_sim.should_merge(temp_entity, existing_entity, weighted_score)
                threshold = DeduplicationConfig.get_merge_threshold_for_type(temp_entity.type)
                print(f"🔍 SHOULD_MERGE: {should_merge} (threshold: {threshold:.3f} for {temp_entity.type})")
                
                if debug_config['show_separator']:
                    print("─" * debug_config['separator_length'])
                
                if should_merge and weighted_score > best_score:
                    best_match = existing_id
                    best_score = weighted_score
                    print(f"🔍 NEW BEST MATCH: {existing_id} with score {weighted_score:.3f}")
            
            if best_match:
                merge_decisions[chunk_idx] = best_match
                print(f"🔍 FINAL DECISION: MERGE '{temp_entity.name}' → '{existing_entities[best_match].name}'")
            else:
                print(f"🔍 FINAL DECISION: CREATE NEW entity '{temp_entity.name}'")
        
        return merge_decisions
    
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
        """SMART merge using EntityMerger instead of stupid replacement logic"""
        try:
            existing_entity = self.semantic_store.entities[existing_entity_id]
            new_entity = self._convert_to_stored_entity(entity)
            
            # Create cluster for EntityMerger (canonical + new entity)
            cluster_entities = {
                existing_entity_id: existing_entity,
                f"new_{entity.name}": new_entity
            }
            
            print(f"🧠 SMART MERGE: Using EntityMerger for '{entity.name}' → '{existing_entity.name}'")
            
            # Delegate to EntityMerger for SMART merging
            canonical_id, merged_entity, relationships = self.semantic_store.merger.merge_entity_cluster(cluster_entities)
            
            # Add chunk reference to merged entity
            merged_entity.add_source_chunk(chunk_id)
            merged_entity.add_document_source(
                self.semantic_store.chunks[chunk_id].document_source if chunk_id in self.semantic_store.chunks else "unknown"
            )
            
            # Update store with merged result
            self.semantic_store.entities[existing_entity_id] = merged_entity
            
            # Update ExtractedEntity reference
            entity.semantic_store_id = existing_entity_id
            
            print(f"✨ SMART MERGE complete: {len(cluster_entities)} entities → 1, {len(relationships)} relationships")
            
        except Exception as e:
            logger.warning(f"⚠️ SMART merge failed, falling back to simple merge: {e}")
            # Fallback to simple merge
            self._simple_merge_fallback(entity, existing_entity_id, chunk_id)
    
    def _simple_merge_fallback(self, entity: ExtractedEntity, existing_entity_id: str, chunk_id: str):
        """Fallback simple merge if EntityMerger fails"""
        existing_entity = self.semantic_store.entities[existing_entity_id]
        
        # Simple concatenation instead of replacement
        if entity.description.strip() and existing_entity.description.strip():
            if entity.description not in existing_entity.description:
                existing_entity.description = f"{existing_entity.description}. {entity.description}"
        elif entity.description.strip():
            existing_entity.description = entity.description
        
        # Keep higher confidence
        if entity.confidence > existing_entity.confidence:
            existing_entity.confidence = entity.confidence
        
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