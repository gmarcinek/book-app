"""
ner/storage/store.py

SemanticStore with batch clustering + entity_config - MINIMAL refactor
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
    """Main semantic store with batch clustering and centralized config"""
    
    def __init__(self,
                storage_dir: str = "semantic_store",
                embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.storage_dir = Path(storage_dir)
        
        logger.info(f"🏗️ Initializing SemanticStore at {self.storage_dir}")
        
        # Core components
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
        
        logger.info(f"✅ SemanticStore ready: {len(self.entities)} entities, {len(self.chunks)} chunks")
    
    def register_chunk(self, chunk_data: Dict[str, Any]) -> str:
        """Register new chunk"""
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
    
    def persist_chunk_with_entities(self, chunk_id: str, entity_ids: List[str]) -> bool:
        """Persist chunk with its entities"""
        if chunk_id not in self.chunks:
            logger.error(f"❌ Chunk {chunk_id} not found")
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
            
            logger.debug(f"💾 Persisted chunk {chunk_id} with {len(entity_ids)} entities")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to persist chunk {chunk_id}: {e}")
            return False
    
    def discover_cross_chunk_relationships(self) -> int:
        """Discover relationships across chunks"""
        try:
            structural_relationships = self.relationship_manager.discover_structural_relationships(
                self.entities, self.chunks
            )
            
            logger.info(f"🔍 Discovered {len(structural_relationships)} relationships")
            return len(structural_relationships)
            
        except Exception as e:
            logger.error(f"❌ Failed to discover relationships: {e}")
            return 0
    
    def get_contextual_entities_for_ner(self, chunk_text: str, max_entities: int = 10, threshold: float = None) -> List[Dict[str, Any]]:
        """Get contextual entities using user-provided or config threshold"""
        if not chunk_text.strip() or not self.entities:
            return []
        
        try:
            chunk_embedding = self.embedder._get_cached_embedding(chunk_text, "temp_chunk")
            
            # Use user threshold or fallback to config
            search_threshold = threshold if threshold is not None else DeduplicationConfig.CONTEXTUAL_ENTITIES_THRESHOLD
            
            similar_entities = self.faiss_manager.search_similar_entities_by_context(
                chunk_embedding, 
                threshold=search_threshold,  # ← USER THRESHOLD
                max_results=max_entities
            )
            
            contextual_entities = []
            for entity_id, similarity in similar_entities:
                if entity_id in self.entities:
                    entity = self.entities[entity_id]
                    contextual_entities.append({
                        'name': entity.name,
                        'type': entity.type,
                        'aliases': entity.aliases[:5],
                        'description': entity.description[:150],
                        'confidence': entity.confidence
                    })
            
            return contextual_entities
            
        except Exception as e:
            logger.error(f"❌ Failed to get contextual entities: {e}")
            return []

    
    def get_known_aliases_for_chunk(self, chunk_text: str) -> Dict[str, List[str]]:
        """Get known aliases for entities in chunk"""
        if not chunk_text.strip() or not self.entities:
            return {}
        
        known_aliases = {}
        chunk_lower = chunk_text.lower()
        
        for entity in self.entities.values():
            if entity.name.lower() in chunk_lower and entity.aliases:
                known_aliases[entity.name] = entity.aliases
        
        return known_aliases
    
    def save_to_disk(self) -> bool:
        """Save all data to disk"""
        try:
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
                **self.get_stats()
            }
            self.persistence.save_metadata(metadata)
            
            logger.info("💾 Semantic store saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save: {e}")
            return False
    
    def _load_existing_data(self):
        """Load existing data from disk"""
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
                self.union_find.add_entity(entity.id)
            
            self.chunks = self.persistence.load_all_chunks()
            for chunk in self.chunks.values():
                self.embedder.update_chunk_embedding(chunk)
                self.faiss_manager.add_chunk(chunk)
            
            loaded_graph = self.persistence.load_graph()
            if loaded_graph:
                self.relationship_manager.graph = loaded_graph
            
            logger.info(f"📂 Loaded: {len(self.entities)} entities, {len(self.chunks)} chunks")
            
        except Exception as e:
            logger.error(f"❌ Failed to load existing data: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        return {
            'entities': len(self.entities),
            'chunks': len(self.chunks),
            'clusters': self.union_find.get_cluster_count(),
            'faiss': self.faiss_manager.get_stats(),
            'relationships': self.relationship_manager.get_relationship_stats(),
            'storage': self.persistence.get_storage_stats(),
            'embedder': self.embedder.get_cache_stats()
        }
    
    # Simple getters
    def get_entity_by_id(self, entity_id: str) -> Optional[StoredEntity]:
        return self.entities.get(entity_id)
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[StoredChunk]:
        return self.chunks.get(chunk_id)
    
    def search_entities_by_name(self, query: str, max_results: int = 10) -> List[Tuple[StoredEntity, float]]:
        """Search entities using centralized config thresholds"""
        if not query.strip():
            return []
        
        query_embedding = self.embedder._get_cached_embedding(f"{query} ENTITY", "search")
        similar_entities = self.faiss_manager.search_similar_entities_by_name(
            query_embedding, 
            threshold=DeduplicationConfig.NAME_SEARCH_THRESHOLD, 
            max_results=max_results
        )
        
        results = []
        for entity_id, similarity in similar_entities:
            if entity_id in self.entities:
                results.append((self.entities[entity_id], similarity))
        
        return results
    
    def create_backup(self, backup_name: Optional[str] = None) -> bool:
        return self.persistence.create_backup(backup_name)