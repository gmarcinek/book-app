"""
test/test_storage_basic.py

Basic tests for SemanticStore components without LLM dependencies
Tests core FAISS operations, embeddings, and persistence
"""

import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np

# Import storage components
import sys
sys.path.append(str(Path(__file__).parent.parent))

from ner.storage import (
    SemanticStore, 
    StoredEntity, 
    StoredChunk, 
    EntityEmbedder,
    FAISSManager,
    StoragePersistence
)


class TestEntityEmbedder:
    """Test EntityEmbedder functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        # Mock SentenceTransformer to avoid downloading models
        with patch('ner.storage.embedder.SentenceTransformer') as mock_st:
            # Create mock model
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_model.encode.return_value = np.random.rand(384).astype(np.float32)
            mock_st.return_value = mock_model
            
            self.embedder = EntityEmbedder(model_name="test-model", cache_embeddings=True)
    
    def test_generate_entity_embeddings(self):
        """Test dual embedding generation for entities"""
        entity = StoredEntity(
            id="test_entity_1",
            name="Jan Kowalski", 
            type="OSOBA",
            description="Główny bohater książki",
            confidence=0.9,
            aliases=["Jan", "Janek"],
            context="Jan Kowalski mieszka w Warszawie"
        )
        
        # Generate embeddings
        name_embedding, context_embedding = self.embedder.generate_entity_embeddings(entity)
        
        # Verify embeddings
        assert name_embedding is not None
        assert context_embedding is not None
        assert name_embedding.shape == (384,)
        assert context_embedding.shape == (384,)
        assert name_embedding.dtype == np.float32
        assert context_embedding.dtype == np.float32
    
    def test_embedding_caching(self):
        """Test embedding caching functionality"""
        # First call should cache
        text = "Test text for caching"
        embedding1 = self.embedder._get_cached_embedding(text, "test")
        
        # Second call should return cached result
        embedding2 = self.embedder._get_cached_embedding(text, "test")
        
        # Should be identical (same cache entry)
        np.testing.assert_array_equal(embedding1, embedding2)
        
        # Cache should have entry
        assert len(self.embedder._embedding_cache) > 0
    
    def test_similarity_computation(self):
        """Test cosine similarity computation"""
        # Create test embeddings
        embedding1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        embedding2 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        embedding3 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        
        # Test orthogonal vectors (similarity = 0)
        similarity_orthogonal = self.embedder.compute_similarity(embedding1, embedding2)
        assert abs(similarity_orthogonal - 0.0) < 0.001
        
        # Test identical vectors (similarity = 1)
        similarity_identical = self.embedder.compute_similarity(embedding1, embedding3)
        assert abs(similarity_identical - 1.0) < 0.001
        
        # Test None handling
        similarity_none = self.embedder.compute_similarity(embedding1, None)
        assert similarity_none == 0.0


class TestFAISSManager:
    """Test FAISS indices management"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.faiss_manager = FAISSManager(embedding_dim=384, storage_dir=self.temp_dir)
    
    def teardown_method(self):
        """Cleanup test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_add_entity_to_faiss(self):
        """Test adding entity to FAISS indices"""
        # Create test entity with embeddings
        entity = StoredEntity(
            id="test_entity_1",
            name="Test Entity",
            type="OSOBA", 
            description="Test description",
            confidence=0.8,
            name_embedding=np.random.rand(384).astype(np.float32),
            context_embedding=np.random.rand(384).astype(np.float32)
        )
        
        # Add to FAISS
        success = self.faiss_manager.add_entity(entity)
        assert success
        
        # Verify indices updated
        assert self.faiss_manager.entity_name_index.ntotal == 1
        assert self.faiss_manager.entity_context_index.ntotal == 1
        assert entity.id in self.faiss_manager.entity_id_to_name_idx
        assert entity.id in self.faiss_manager.entity_id_to_context_idx
    
    def test_search_similar_entities(self):
        """Test semantic search in FAISS"""
        # Add test entities
        entities = []
        for i in range(3):
            entity = StoredEntity(
                id=f"test_entity_{i}",
                name=f"Entity {i}",
                type="OSOBA",
                description="Test description",
                confidence=0.8,
                name_embedding=np.random.rand(384).astype(np.float32),
                context_embedding=np.random.rand(384).astype(np.float32)
            )
            # Normalize embeddings for FAISS inner product
            entity.name_embedding = entity.name_embedding / np.linalg.norm(entity.name_embedding)
            entity.context_embedding = entity.context_embedding / np.linalg.norm(entity.context_embedding)
            
            entities.append(entity)
            self.faiss_manager.add_entity(entity)
        
        # Search for similar entities
        query_embedding = np.random.rand(384).astype(np.float32)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        
        results = self.faiss_manager.search_similar_entities_by_name(
            query_embedding, threshold=0.0, max_results=5
        )
        
        # Should find all entities (threshold=0.0)
        assert len(results) == 3
        
        # Results should be tuples of (entity_id, similarity_score)
        for entity_id, similarity in results:
            assert entity_id.startswith("test_entity_")
            assert 0.0 <= similarity <= 1.0
    
    def test_chunk_operations(self):
        """Test chunk storage and search"""
        # Create test chunk
        chunk = StoredChunk(
            id="test_chunk_1",
            text="This is a test chunk with some content",
            document_source="test_document.txt",
            text_embedding=np.random.rand(384).astype(np.float32)
        )
        
        # Add to FAISS
        success = self.faiss_manager.add_chunk(chunk)
        assert success
        assert self.faiss_manager.chunk_index.ntotal == 1
        
        # Search chunks
        query_embedding = np.random.rand(384).astype(np.float32)
        results = self.faiss_manager.search_similar_chunks(
            query_embedding, threshold=0.0, max_results=5
        )
        
        assert len(results) == 1
        chunk_id, similarity = results[0]
        assert chunk_id == "test_chunk_1"


class TestSemanticStore:
    """Integration test for SemanticStore"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Mock SentenceTransformer
        with patch('ner.storage.embedder.SentenceTransformer') as mock_st:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_model.encode.return_value = np.random.rand(384).astype(np.float32)
            mock_st.return_value = mock_model
            
            self.store = SemanticStore(
                storage_dir=str(self.temp_dir),
                embedding_model="test-model"
            )
    
    def teardown_method(self):
        """Cleanup test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_register_chunk(self):
        """Test chunk registration"""
        chunk_data = {
            'text': 'Jan Kowalski mieszka w Warszawie i pracuje jako nauczyciel.',
            'document_source': 'test_book.txt',
            'start_pos': 0,
            'end_pos': 100,
            'chunk_index': 0
        }
        
        chunk_id = self.store.register_chunk(chunk_data)
        
        assert chunk_id is not None
        assert chunk_id in self.store.chunks
        assert self.store.chunks[chunk_id].text == chunk_data['text']
    
    def test_add_entity_with_deduplication(self):
        """Test entity addition with semantic deduplication"""
        # Register a chunk first
        chunk_data = {
            'text': 'Test chunk with entities',
            'document_source': 'test.txt',
            'chunk_index': 0
        }
        chunk_id = self.store.register_chunk(chunk_data)
        
        # Add first entity
        entity_data_1 = {
            'name': 'Jan Kowalski',
            'type': 'OSOBA',
            'description': 'Główny bohater książki',
            'confidence': 0.9,
            'aliases': ['Jan', 'Janek'],
            'context': 'Jan Kowalski mieszka w mieście'
        }
        
        entity_id_1, is_new_1, aliases_1 = self.store.add_entity_with_deduplication(
            entity_data_1, chunk_id
        )
        
        assert is_new_1  # First entity should be new
        assert entity_id_1 in self.store.entities
        assert len(aliases_1) == 0  # No aliases discovered yet
        
        # Add similar entity (should be merged due to semantic similarity)
        entity_data_2 = {
            'name': 'Jan Kowalski',  # Same name
            'type': 'OSOBA',
            'description': 'Bohater opowieści',  # Different description
            'confidence': 0.95,  # Higher confidence
            'aliases': ['Kowalski', 'JK'],  # Different aliases
            'context': 'Jan Kowalski lubi czytać książki'
        }
        
        # Mock high similarity to force merge
        with patch.object(self.store.faiss_manager, 'search_similar_entities_by_name') as mock_search:
            mock_search.return_value = [(entity_id_1, 0.95)]  # High similarity
            
            entity_id_2, is_new_2, aliases_2 = self.store.add_entity_with_deduplication(
                entity_data_2, chunk_id
            )
        
        assert not is_new_2  # Should be merged, not new
        assert entity_id_2 == entity_id_1  # Same entity ID
        assert len(aliases_2) > 0  # Should discover new aliases
        
        # Check that entity was updated
        updated_entity = self.store.entities[entity_id_1]
        assert updated_entity.confidence == 0.95  # Higher confidence
        assert 'Kowalski' in updated_entity.aliases  # New alias added
        assert 'JK' in updated_entity.aliases  # New alias added
    
    def test_contextual_entity_discovery(self):
        """Test contextual entity discovery for NER enhancement"""
        # Add some entities first
        chunk_data = {
            'text': 'Test chunk',
            'document_source': 'test.txt', 
            'chunk_index': 0
        }
        chunk_id = self.store.register_chunk(chunk_data)
        
        entity_data = {
            'name': 'Warszawa',
            'type': 'MIEJSCE',
            'description': 'Stolica Polski',
            'confidence': 0.9,
            'aliases': ['stolica', 'WWA'],
            'context': 'Warszawa jest największym miastem w Polsce'
        }
        
        self.store.add_entity_with_deduplication(entity_data, chunk_id)
        
        # Now test contextual discovery
        query_text = "Mieszkam w stolicy Polski i bardzo mi się podoba."
        
        # Mock FAISS search to return our entity
        with patch.object(self.store.faiss_manager, 'search_similar_entities_by_context') as mock_search:
            entity_id = list(self.store.entities.keys())[0]
            mock_search.return_value = [(entity_id, 0.8)]
            
            contextual_entities = self.store.get_contextual_entities_for_ner(query_text, max_entities=5)
        
        assert len(contextual_entities) > 0
        
        # Check structure of returned entities
        entity = contextual_entities[0]
        assert 'name' in entity
        assert 'type' in entity
        assert 'aliases' in entity
        assert 'description' in entity
        assert 'confidence' in entity
        
        assert entity['name'] == 'Warszawa'
        assert entity['type'] == 'MIEJSCE'
    
    def test_persistence_cycle(self):
        """Test save/load cycle"""
        # Add test data
        chunk_data = {
            'text': 'Persistence test chunk',
            'document_source': 'test.txt',
            'chunk_index': 0
        }
        chunk_id = self.store.register_chunk(chunk_data)
        
        entity_data = {
            'name': 'Test Entity',
            'type': 'OSOBA',
            'description': 'Entity for persistence test',
            'confidence': 0.8,
            'aliases': ['test', 'entity'],
            'context': 'Test context'
        }
        
        entity_id, _, _ = self.store.add_entity_with_deduplication(entity_data, chunk_id)
        
        # Save to disk
        save_success = self.store.save_to_disk()
        assert save_success
        
        # Verify files exist
        assert (self.temp_dir / "entities" / f"{entity_id}.json").exists()
        assert (self.temp_dir / "chunks" / f"{chunk_id}.json").exists()
        
        # Test stats
        stats = self.store.get_stats()
        assert stats['entities'] == 1
        assert stats['chunks'] == 1
        assert 'faiss' in stats
        assert 'relationships' in stats


if __name__ == "__main__":
    # Run specific test
    import sys
    
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        if test_name == "embedder":
            pytest.main(["-v", "test/test_storage_basic.py::TestEntityEmbedder"])
        elif test_name == "faiss":
            pytest.main(["-v", "test/test_storage_basic.py::TestFAISSManager"])
        elif test_name == "store":
            pytest.main(["-v", "test/test_storage_basic.py::TestSemanticStore"])
        else:
            pytest.main(["-v", "test/test_storage_basic.py"])
    else:
        # Run all tests
        pytest.main(["-v", "test/test_storage_basic.py"])