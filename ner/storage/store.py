"""
SemanticStore with OpenAI embeddings and disk cache
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from .models import StoredEntity, StoredChunk, create_chunk_id
from .embedder import EntityEmbedder
from .indices import FAISSManager  
from .relations import RelationshipManager
from .persistence import StoragePersistence
from .clustering.union_find import EntityUnionFind
from .clustering.merger import EntityMerger
from .similarity.engine import EntitySimilarityEngine
from ..entity_config import DeduplicationConfig

logger = logging.getLogger(__name__)


class SemanticStore:
   """Semantic store with OpenAI embeddings and caching"""
   
   def __init__(self,
               storage_dir: str = "semantic_store",
               embedding_model: str = "text-embedding-3-small"):
       # Initialize semantic store with OpenAI embeddings
       self.storage_dir = Path(storage_dir)
       
       print(f"🏗️ Initializing SemanticStore at {self.storage_dir}")
       logger.info(f"🏗️ Initializing SemanticStore at {self.storage_dir}")
       
       # Core components with OpenAI embeddings
       self.embedder = EntityEmbedder(embedding_model)
       self.persistence = StoragePersistence(self.storage_dir)
       self.faiss_manager = FAISSManager(self.embedder.embedding_dim, self.storage_dir / "faiss")
       self.relationship_manager = RelationshipManager()
       
       # Clustering components
       self.union_find = EntityUnionFind()
       self.merger = EntityMerger()
       self.similarity_engine = EntitySimilarityEngine(self.relationship_manager)
       
       # Data storage
       self.entities: Dict[str, StoredEntity] = {}
       self.chunks: Dict[str, StoredChunk] = {}
       
       self._load_existing_data()
       
       print(f"✅ SemanticStore ready: {len(self.entities)} entities, {len(self.chunks)} chunks")
       logger.info(f"✅ SemanticStore ready: {len(self.entities)} entities, {len(self.chunks)} chunks")
   
   def register_chunk(self, chunk_data: Dict[str, Any]) -> str:
       # Register new chunk with metadata
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
       print(f"📝 Registered chunk: {chunk_id}")
       return chunk_id
   
   def persist_chunk_with_entities(self, chunk_id: str, entity_ids: List[str]) -> bool:
       # Persist chunk with its entities
       if chunk_id not in self.chunks:
           print(f"❌ Chunk {chunk_id} not found")
           return False
       
       try:
           chunk = self.chunks[chunk_id]
           chunk.entity_ids = entity_ids
           chunk.mark_processed()
           
           # Generate and add chunk embedding
           self.embedder.update_chunk_embedding(chunk)
           self.faiss_manager.add_chunk(chunk)
           
           # Create relationships
           relationships = self.relationship_manager.add_chunk_entity_relationships(chunk, entity_ids)
           
           # Save to disk
           self.persistence.save_chunk(chunk)
           
           for entity_id in entity_ids:
               if entity_id in self.entities:
                   self.persistence.save_entity(self.entities[entity_id])
           
           print(f"💾 Persisted chunk {chunk_id} with {len(entity_ids)} entities")
           return True
           
       except Exception as e:
           print(f"❌ Failed to persist chunk {chunk_id}: {e}")
           return False
   
   def discover_cross_chunk_relationships(self) -> int:
       # Discover relationships across chunks
       try:
           structural_relationships = self.relationship_manager.discover_structural_relationships(
               self.entities, self.chunks
           )
           
           print(f"🔍 Discovered {len(structural_relationships)} cross-chunk relationships")
           return len(structural_relationships)
           
       except Exception as e:
           print(f"❌ Failed to discover relationships: {e}")
           return 0
   
   def get_contextual_entities_for_ner(self, chunk_text: str, max_entities: int = 10, threshold: float = None) -> List[Dict[str, Any]]:
       # Get contextual entities using semantic similarity
       if not chunk_text.strip() or not self.entities:
           return []
       
       try:
           # Generate embedding for chunk text
           chunk_embedding = self.embedder._get_embedding_with_cache(chunk_text)
           
           # Use provided threshold or config default
           search_threshold = threshold if threshold is not None else DeduplicationConfig.CONTEXTUAL_ENTITIES_THRESHOLD
           
           # Search similar entities
           similar_entities = self.faiss_manager.search_similar_entities_by_context(
               chunk_embedding, 
               threshold=search_threshold,
               max_results=max_entities
           )
           
           # Format results
           contextual_entities = []
           for entity_id, similarity in similar_entities:
               if entity_id in self.entities:
                   entity = self.entities[entity_id]
                   contextual_entities.append({
                       'id': entity.id,
                       'name': entity.name,
                       'type': entity.type,
                       'aliases': entity.aliases[:10],
                       'description': entity.description,
                       'confidence': entity.confidence
                   })
           
           if contextual_entities:
               print(f"🔍 Found {len(contextual_entities)} contextual entities for chunk")
           
           return contextual_entities
           
       except Exception as e:
           print(f"❌ Failed to get contextual entities: {e}")
           return []
   
   def save_to_disk(self) -> bool:
       # Save all data to disk
       try:
           print(f"💾 Saving semantic store...")
           
           # Save entities and chunks
           for entity in self.entities.values():
               self.persistence.save_entity(entity)
           
           for chunk in self.chunks.values():
               self.persistence.save_chunk(chunk)
           
           # Save FAISS indices
           self.faiss_manager.save_to_disk()
           
           # Save graph
           self.persistence.save_graph(self.relationship_manager.graph)
           
           # Save metadata
           metadata = {
               'entity_count': len(self.entities),
               'chunk_count': len(self.chunks),
               'embedding_model': self.embedder.model_name,
               **self.get_stats()
           }
           self.persistence.save_metadata(metadata)
           
           print("💾 Semantic store saved successfully")
           return True
           
       except Exception as e:
           print(f"❌ Failed to save semantic store: {e}")
           return False
   
   def _load_existing_data(self):
       # Load existing data from disk
       try:
           if not self.persistence.exists():
               print("📂 No existing storage found, starting fresh")
               return
           
           print("📂 Loading existing semantic store...")
           
           # Load entities
           self.entities = self.persistence.load_all_entities()
           for entity in self.entities.values():
               # Regenerate embeddings (OpenAI model might be different)
               self.embedder.update_entity_embeddings(entity)
               self.faiss_manager.add_entity(entity)
               self.relationship_manager.add_entity_node(entity)
               self.union_find.add_entity(entity.id)
           
           # Load chunks
           self.chunks = self.persistence.load_all_chunks()
           for chunk in self.chunks.values():
               # Regenerate embeddings
               self.embedder.update_chunk_embedding(chunk)
               self.faiss_manager.add_chunk(chunk)
           
           # Load graph
           loaded_graph = self.persistence.load_graph()
           if loaded_graph:
               self.relationship_manager.graph = loaded_graph
           
           print(f"📂 Loaded: {len(self.entities)} entities, {len(self.chunks)} chunks")
           
       except Exception as e:
           print(f"❌ Failed to load existing data: {e}")
   
   def get_stats(self) -> Dict[str, Any]:
       # Get comprehensive statistics
       return {
           'entities': len(self.entities),
           'chunks': len(self.chunks),
           'clusters': self.union_find.get_cluster_count(),
           'faiss': self.faiss_manager.get_stats(),
           'relationships': self.relationship_manager.get_relationship_stats(),
           'storage': self.persistence.get_storage_stats(),
           'embedder': self.embedder.get_cache_stats()
       }
   
   def get_entity_by_id(self, entity_id: str) -> Optional[StoredEntity]:
       # Get entity by ID
       return self.entities.get(entity_id)
   
   def get_chunk_by_id(self, chunk_id: str) -> Optional[StoredChunk]:
       # Get chunk by ID
       return self.chunks.get(chunk_id)
   
   def search_entities_by_name(self, query: str, max_results: int = None) -> List[Tuple[StoredEntity, float]]:
       # Search entities by name using semantic similarity
       if not query.strip():
           return []
       
       # Use config defaults if not specified
       threshold = DeduplicationConfig.NAME_SEARCH_THRESHOLD
       max_results = max_results or DeduplicationConfig.NAME_SEARCH_MAX_RESULTS
       
       # Generate query embedding
       query_embedding = self.embedder._get_embedding_with_cache(f"{query} ENTITY")
       
       # Search using FAISS
       similar_entities = self.faiss_manager.search_similar_entities_by_name(
           query_embedding, 
           threshold=threshold, 
           max_results=max_results
       )
       
       # Convert to results
       results = []
       for entity_id, similarity in similar_entities:
           if entity_id in self.entities:
               results.append((self.entities[entity_id], similarity))
       
       if results:
           print(f"🔍 Name search '{query}': {len(results)} results")
       
       return results
   
   def create_backup(self, backup_name: Optional[str] = None) -> bool:
       # Create backup of semantic store
       return self.persistence.create_backup(backup_name)
   
   def clear_cache(self):
       # Clear embeddings cache
       self.embedder.clear_cache()
       print("🧹 Semantic store cache cleared")