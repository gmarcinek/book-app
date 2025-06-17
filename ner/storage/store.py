# ner/storage/store.py

"""
ner/storage/store.py

Main SemanticStore coordinator integrating all storage components
Provides real-time semantic enhancement for EntityExtractor
"""

import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from .models import StoredEntity, StoredChunk, create_entity_id, create_chunk_id
from .embedder import EntityEmbedder
from .indices import FAISSManager  
from .relations import RelationshipManager
from .persistence import StoragePersistence

logger = logging.getLogger(__name__)


class SemanticStore:
   """Main semantic store integrating FAISS, NetworkX, and persistence"""
   
   def __init__(self,
                storage_dir: str = "semantic_store",
                embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
                name_similarity_threshold: float = 0.85,
                context_similarity_threshold: float = 0.7):
       self.storage_dir = Path(storage_dir)
       self.name_similarity_threshold = name_similarity_threshold
       self.context_similarity_threshold = context_similarity_threshold
       
       logger.info(f"🏗️ Initializing SemanticStore at {self.storage_dir}")
       
       self.embedder = EntityEmbedder(embedding_model)
       self.persistence = StoragePersistence(self.storage_dir)
       self.faiss_manager = FAISSManager(self.embedder.embedding_dim, self.storage_dir / "faiss")
       self.relationship_manager = RelationshipManager()
       
       self.entities: Dict[str, StoredEntity] = {}
       self.chunks: Dict[str, StoredChunk] = {}
       
       self._load_existing_data()
       
       logger.info(f"✅ SemanticStore ready: {len(self.entities)} entities, {len(self.chunks)} chunks")
   
   def register_chunk(self, chunk_data: Dict[str, Any]) -> str:
       chunk_id = chunk_data.get('id')
       if not chunk_id:
           chunk_index = chunk_data.get('chunk_index', 0)
           document_source = chunk_data.get('document_source', 'unknown')
           chunk_id = create_chunk_id(document_source, chunk_index)
       
       chunk = StoredChunk(
           id=chunk_id,
           text=chunk_data.get('text', ''),
           document_source=chunk_data.get('document_source', ''),
           start_pos=chunk_data.get('start_pos', 0),
           end_pos=chunk_data.get('end_pos', 0)
       )
       
       self.chunks[chunk_id] = chunk
       
       logger.debug(f"📝 Registered chunk: {chunk_id}")
       return chunk_id
   
   def get_contextual_entities_for_ner(self, chunk_text: str, max_entities: int = 10) -> List[Dict[str, Any]]:
       if not chunk_text.strip() or not self.entities:
           return []
       
       logger.debug(f"🎯 Getting contextual entities for chunk ({len(chunk_text)} chars)")
       
       try:
           chunk_embedding = self.embedder._get_cached_embedding(chunk_text, "temp_chunk")
           
           similar_entities = self.faiss_manager.search_similar_entities_by_context(
               chunk_embedding,
               threshold=self.context_similarity_threshold,
               max_results=max_entities
           )
           
           similar_chunks = self.faiss_manager.search_similar_chunks(
               chunk_embedding,
               threshold=0.6,
               max_results=3
           )
           
           relevant_entity_ids = set()
           for entity_id, similarity in similar_entities:
               relevant_entity_ids.add(entity_id)
           
           for chunk_id, similarity in similar_chunks:
               if chunk_id in self.chunks:
                   relevant_entity_ids.update(self.chunks[chunk_id].entity_ids)
           
           contextual_entities = []
           for entity_id in list(relevant_entity_ids)[:max_entities]:
               if entity_id in self.entities:
                   entity = self.entities[entity_id]
                   contextual_entities.append({
                       'name': entity.name,
                       'type': entity.type,
                       'aliases': entity.aliases[:5],
                       'description': entity.description[:150],
                       'confidence': entity.confidence
                   })
           
           logger.info(f"🎯 Found {len(contextual_entities)} contextual entities for NER enhancement")
           return contextual_entities
           
       except Exception as e:
           logger.error(f"❌ Failed to get contextual entities: {e}")
           return []
   
   def get_known_aliases_for_chunk(self, chunk_text: str) -> Dict[str, List[str]]:
       if not chunk_text.strip() or not self.entities:
           return {}
       
       known_aliases = {}
       chunk_lower = chunk_text.lower()
       
       for entity in self.entities.values():
           if entity.name.lower() in chunk_lower:
               if entity.aliases:
                   known_aliases[entity.name] = entity.aliases
           
           for alias in entity.aliases:
               if alias.lower() in chunk_lower:
                   if entity.name not in known_aliases:
                       known_aliases[entity.name] = entity.aliases
                   break
       
       logger.debug(f"🏷️ Found {len(known_aliases)} entities with known aliases in chunk")
       return known_aliases
   
   def add_entity_with_deduplication(self, 
                                   entity_data: Dict[str, Any], 
                                   chunk_id: str) -> Tuple[str, bool, List[str]]:
       name = entity_data.get('name', '').strip()
       entity_type = entity_data.get('type', '').strip()
       description = entity_data.get('description', '')
       confidence = entity_data.get('confidence', 0.5)
       aliases = entity_data.get('aliases', [])
       context = entity_data.get('context', '')
       
       if not name or not entity_type:
           raise ValueError(f"Entity missing name or type: {entity_data}")
       
       temp_entity = StoredEntity(
           id="temp",
           name=name,
           type=entity_type,
           description=description,
           confidence=confidence,
           aliases=aliases,
           context=context
       )
       
       name_embedding, context_embedding = self.embedder.generate_entity_embeddings(temp_entity)
       temp_entity.name_embedding = name_embedding
       temp_entity.context_embedding = context_embedding
       
       name_only_text = name
       name_only_embedding = self.embedder._get_cached_embedding(name_only_text, "name_only")
       
       similar_by_name = self.faiss_manager.search_similar_entities_by_name(
           name_only_embedding,
           threshold=self.name_similarity_threshold,
           max_results=5
       )
       
       if similar_by_name:
           existing_id, similarity_score = similar_by_name[0]
           existing_entity = self.entities[existing_id]
           
           logger.info(f"🔗 Merging '{name}' with existing '{existing_entity.name}' (similarity: {similarity_score:.3f})")
           
           discovered_aliases = self._merge_entity_data(existing_entity, temp_entity)
           
           existing_entity.add_source_chunk(chunk_id)
           existing_entity.add_document_source(self.chunks[chunk_id].document_source if chunk_id in self.chunks else "unknown")
           
           existing_entity.name_embedding = (existing_entity.name_embedding + name_embedding) / 2
           existing_entity.context_embedding = (existing_entity.context_embedding + context_embedding) / 2
           
           self._normalize_embeddings(existing_entity)
           
           return existing_id, False, discovered_aliases
       
       else:
           entity_id = create_entity_id(name, entity_type)
           temp_entity.id = entity_id
           temp_entity.add_source_chunk(chunk_id)
           temp_entity.add_document_source(self.chunks[chunk_id].document_source if chunk_id in self.chunks else "unknown")
           
           self.faiss_manager.add_entity(temp_entity)
           self.relationship_manager.add_entity_node(temp_entity)
           self.entities[entity_id] = temp_entity
           
           logger.info(f"✨ Created new entity: '{name}' ({entity_type}) [id: {entity_id}]")
           return entity_id, True, []
   
   def persist_chunk_with_entities(self, 
                                 chunk_id: str, 
                                 entity_ids: List[str]) -> bool:
       if chunk_id not in self.chunks:
           logger.error(f"❌ Chunk {chunk_id} not found for persistence")
           return False
       
       try:
           chunk = self.chunks[chunk_id]
           
           chunk.entity_ids = entity_ids
           chunk.mark_processed()
           
           self.embedder.update_chunk_embedding(chunk)
           self.faiss_manager.add_chunk(chunk)
           
           relationships = self.relationship_manager.add_chunk_entity_relationships(chunk, entity_ids)
           
           self.persistence.save_chunk(chunk)
           
           for entity_id in entity_ids:
               if entity_id in self.entities:
                   self.persistence.save_entity(self.entities[entity_id])
           
           logger.info(f"💾 Persisted chunk {chunk_id} with {len(entity_ids)} entities and {len(relationships)} relationships")
           return True
           
       except Exception as e:
           logger.error(f"❌ Failed to persist chunk {chunk_id}: {e}")
           return False
   
   def discover_cross_chunk_relationships(self) -> int:
       logger.info("🔍 Discovering cross-chunk relationships...")
       
       try:
           structural_relationships = self.relationship_manager.discover_structural_relationships(
               self.entities, self.chunks
           )
           
           total_discovered = len(structural_relationships)
           logger.info(f"🔍 Discovered {total_discovered} cross-chunk relationships")
           
           return total_discovered
           
       except Exception as e:
           logger.error(f"❌ Failed to discover cross-chunk relationships: {e}")
           return 0
   
   def save_to_disk(self) -> bool:
       try:
           logger.info("💾 Saving semantic store to disk...")
           
           for entity in self.entities.values():
               self.persistence.save_entity(entity)
           
           for chunk in self.chunks.values():
               self.persistence.save_chunk(chunk)
           
           self.faiss_manager.save_to_disk()
           
           self.persistence.save_graph(self.relationship_manager.graph)
           
           metadata = {
               'entity_count': len(self.entities),
               'chunk_count': len(self.chunks),
               'embedding_model': self.embedder.model_name,
               'name_similarity_threshold': self.name_similarity_threshold,
               'context_similarity_threshold': self.context_similarity_threshold,
               **self.get_stats()
           }
           self.persistence.save_metadata(metadata)
           
           logger.info(f"💾 Semantic store saved successfully")
           return True
           
       except Exception as e:
           logger.error(f"❌ Failed to save semantic store: {e}")
           return False
   
   def _load_existing_data(self):
       try:
           if not self.persistence.exists():
               logger.info("📂 No existing storage found, starting fresh")
               return
           
           logger.info("📂 Loading existing semantic store...")
           
           self.entities = self.persistence.load_all_entities()
           for entity in self.entities.values():
               self.embedder.update_entity_embeddings(entity)
               self.faiss_manager.add_entity(entity)
               self.relationship_manager.add_entity_node(entity)
           
           self.chunks = self.persistence.load_all_chunks()
           for chunk in self.chunks.values():
               self.embedder.update_chunk_embedding(chunk)
               self.faiss_manager.add_chunk(chunk)
           
           loaded_graph = self.persistence.load_graph()
           if loaded_graph:
               self.relationship_manager.graph = loaded_graph
           
           logger.info(f"📂 Loaded existing data: {len(self.entities)} entities, {len(self.chunks)} chunks")
           
       except Exception as e:
           logger.error(f"❌ Failed to load existing data: {e}")
   
   def _merge_entity_data(self, existing_entity: StoredEntity, new_entity: StoredEntity) -> List[str]:
       discovered_aliases = []
       
       if new_entity.confidence > existing_entity.confidence:
           existing_entity.confidence = new_entity.confidence
       
       if len(new_entity.description) > len(existing_entity.description):
           existing_entity.description = new_entity.description
       
       new_aliases = set(new_entity.aliases)
       if new_entity.name != existing_entity.name:
           new_aliases.add(new_entity.name)
       
       discovered_aliases = existing_entity.merge_aliases(list(new_aliases))
       
       return discovered_aliases
   
   def _normalize_embeddings(self, entity: StoredEntity):
       if entity.name_embedding is not None:
           norm = np.linalg.norm(entity.name_embedding)
           if norm > 0:
               entity.name_embedding = entity.name_embedding / norm
       
       if entity.context_embedding is not None:
           norm = np.linalg.norm(entity.context_embedding)
           if norm > 0:
               entity.context_embedding = entity.context_embedding / norm
   
   def get_stats(self) -> Dict[str, Any]:
       faiss_stats = self.faiss_manager.get_stats()
       relationship_stats = self.relationship_manager.get_relationship_stats()
       storage_stats = self.persistence.get_storage_stats()
       cache_stats = self.embedder.get_cache_stats()
       
       return {
           'entities': len(self.entities),
           'chunks': len(self.chunks),
           'faiss': faiss_stats,
           'relationships': relationship_stats,
           'storage': storage_stats,
           'embedder': cache_stats,
           'thresholds': {
               'name_similarity': self.name_similarity_threshold,
               'context_similarity': self.context_similarity_threshold
           }
       }
   
   def create_backup(self, backup_name: Optional[str] = None) -> bool:
       return self.persistence.create_backup(backup_name)
   
   def get_entity_by_id(self, entity_id: str) -> Optional[StoredEntity]:
       return self.entities.get(entity_id)
   
   def get_chunk_by_id(self, chunk_id: str) -> Optional[StoredChunk]:
       return self.chunks.get(chunk_id)
   
   def search_entities_by_name(self, query: str, max_results: int = 10) -> List[Tuple[StoredEntity, float]]:
       if not query.strip():
           return []
       
       query_embedding = self.embedder._get_cached_embedding(f"{query} ENTITY", "search")
       similar_entities = self.faiss_manager.search_similar_entities_by_name(
           query_embedding, threshold=0.5, max_results=max_results
       )
       
       results = []
       for entity_id, similarity in similar_entities:
           if entity_id in self.entities:
               results.append((self.entities[entity_id], similarity))
       
       return results