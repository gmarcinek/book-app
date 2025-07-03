"""
SemanticStore with OpenAI embeddings and disk cache
KISS version - NO deduplication, just store and retrieve
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from .models import StoredEntity, StoredChunk, create_chunk_id
from .embedder import EntityEmbedder
from .indices import FAISSManager  
from .relations import RelationshipManager
from .persistence import StoragePersistence

logger = logging.getLogger(__name__)


class SemanticStore:
    """Semantic store with OpenAI embeddings - KISS principle"""
    
    def __init__(self,
                storage_dir: str = "semantic_store",
                embedding_model: str = "text-embedding-3-small"):
        self.storage_dir = Path(storage_dir)
        
        print(f"🏗️ Initializing SemanticStore at {self.storage_dir}")
        logger.info(f"🏗️ Initializing SemanticStore at {self.storage_dir}")
        
        # Core components - no clustering crap
        self.embedder = EntityEmbedder(embedding_model)
        self.persistence = StoragePersistence(self.storage_dir)
        self.faiss_manager = FAISSManager(self.embedder.embedding_dim, self.storage_dir / "faiss")
        self.relationship_manager = RelationshipManager()
        
        # Data storage
        self.entities: Dict[str, StoredEntity] = {}
        self.chunks: Dict[str, StoredChunk] = {}
        
        self._load_existing_data()
        
        print(f"✅ SemanticStore ready: {len(self.entities)} entities, {len(self.chunks)} chunks")
        logger.info(f"✅ SemanticStore ready: {len(self.entities)} entities, {len(self.chunks)} chunks")
    
    def register_chunk(self, chunk_data: Dict[str, Any]) -> str:
        """Register new chunk with metadata"""
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
    
    def add_entity(self, entity: StoredEntity) -> str:
        """Add entity directly - NO deduplication, KISS"""
        # Generate embeddings
        self.embedder.update_entity_embeddings(entity)
        
        # Store entity
        self.entities[entity.id] = entity
        
        # Add to FAISS and graph
        self.faiss_manager.add_entity(entity)
        self.relationship_manager.add_entity_node(entity)
        
        logger.debug(f"Added entity {entity.id}: {entity.name}")
        return entity.id
    
    def persist_chunk_with_entities(self, chunk_id: str, entity_ids: List[str]) -> bool:
        """Persist chunk with its entities"""
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
        """Discover relationships across chunks"""
        try:
            structural_relationships = self.relationship_manager.discover_structural_relationships(
                self.entities, self.chunks
            )
            
            print(f"🔍 Discovered {len(structural_relationships)} cross-chunk relationships")
            return len(structural_relationships)
            
        except Exception as e:
            print(f"❌ Failed to discover relationships: {e}")
            return 0
    
    def get_contextual_entities_for_ner(self, chunk_text: str, max_entities: int = 10, threshold: float = 0.6) -> List[Dict[str, Any]]:
        """Get contextual entities using semantic similarity"""
        if not chunk_text.strip() or not self.entities:
            return []
        
        try:
            # Generate embedding for chunk text
            chunk_embedding = self.embedder._get_embedding_with_cache(chunk_text)
            
            # Search similar entities
            similar_entities = self.faiss_manager.search_similar_entities_by_context(
                chunk_embedding, 
                threshold=threshold,
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
        """Save all data to disk - GitHub style"""
        try:
            print(f"💾 Saving semantic store...")
            
            # Save entities and chunks - per item like GitHub
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
        """Load existing data from disk - GitHub style names"""
        try:
            if not self.persistence.exists():
                print("📂 No existing storage found, starting fresh")
                return
            
            print("📂 Loading existing semantic store...")
            
            # Load entities - correct GitHub method names
            self.entities = self.persistence.load_all_entities()
            for entity in self.entities.values():
                # Regenerate embeddings
                self.embedder.update_entity_embeddings(entity)
                self.faiss_manager.add_entity(entity)
                self.relationship_manager.add_entity_node(entity)
                # NO union_find crap
            
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
        """Get storage statistics - GitHub style detailed"""
        entity_types = {}
        for entity in self.entities.values():
            entity_types[entity.type] = entity_types.get(entity.type, 0) + 1
        
        return {
            "entities": len(self.entities),
            "chunks": len(self.chunks),
            "entity_types": entity_types,
            "relationships": self.relationship_manager.get_relationship_count() if hasattr(self.relationship_manager, 'get_relationship_count') else 0
        }
    
    # Additional methods from GitHub that might be used by API
    def search_entities_by_text(self, query: str, 
                              entity_type: str = None,
                              threshold: float = 0.6,
                              max_results: int = 10) -> List[Tuple[str, float]]:
        """Search entities by text similarity"""
        if not query.strip():
            return []
        
        query_embedding = self.embedder.get_text_embedding(query)
        if query_embedding is None:
            return []
        
        # Filter by type if specified
        entities_to_search = self.entities
        if entity_type:
            entities_to_search = {
                eid: entity for eid, entity in self.entities.items()
                if entity.type == entity_type
            }
        
        # Simple similarity search
        results = []
        for entity_id, entity in entities_to_search.items():
            if entity.context_embedding is not None:
                similarity = self.embedder.compute_similarity(
                    query_embedding, entity.context_embedding
                )
                if similarity >= threshold:
                    results.append((entity_id, similarity))
        
        # Sort by similarity and limit
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:max_results]
    
    def search_entities_by_name(self, query: str,
                               threshold: float = 0.8,
                               max_results: int = 5) -> List[Tuple[str, float]]:
        """Search entities by name/alias similarity"""
        if not query.strip():
            return []
        
        query_lower = query.lower().strip()
        results = []
        
        for entity_id, entity in self.entities.items():
            # Check main name
            if query_lower in entity.name.lower():
                score = len(query_lower) / len(entity.name)
                results.append((entity_id, score))
                continue
            
            # Check aliases
            for alias in entity.aliases:
                if query_lower in alias.lower():
                    score = len(query_lower) / len(alias)
                    results.append((entity_id, score))
                    break
        
        # Sort and limit
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:max_results]
    
    def get_entity_relationships(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get all relationships for entity"""
        return self.relationship_manager.get_entity_relationships(entity_id)