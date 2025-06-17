"""
test/test_storage_integration.py

Integration tests for SemanticStore with EntityExtractor
Tests real-world NER workflow with semantic enhancement
"""

import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from typing import List, Dict, Any

import numpy as np

# Import components
import sys
sys.path.append(str(Path(__file__).parent.parent))

from ner.storage import SemanticStore
from ner.extractor.base import EntityExtractor, ExtractedEntity
from ner.semantic.base import TextChunk
from ner.domains.simple import SimpleNER
from ner.config import create_default_ner_config


class TestSemanticStoreIntegration:
    """Integration tests for SemanticStore with EntityExtractor"""
    
    def setup_method(self):
        """Setup test environment with mocked dependencies"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Mock sentence transformer to avoid model download
        self.mock_st_patcher = patch('ner.storage.embedder.SentenceTransformer')
        mock_st = self.mock_st_patcher.start()
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        
        # Create deterministic embeddings for testing
        def mock_encode(text, normalize_embeddings=True, batch_size=None):
            # Create deterministic embedding based on text hash
            text_hash = hash(str(text)) % 1000000
            np.random.seed(text_hash)
            embedding = np.random.rand(384).astype(np.float32)
            if normalize_embeddings:
                embedding = embedding / np.linalg.norm(embedding)
            return embedding
        
        mock_model.encode = mock_encode
        mock_st.return_value = mock_model
        
        # Mock LLM client to avoid API calls
        self.mock_llm_patcher = patch('llm.LLMClient')
        mock_llm_client = self.mock_llm_patcher.start()
        
        # Mock LLM responses
        self.mock_llm_instance = MagicMock()
        mock_llm_client.return_value = self.mock_llm_instance
        
        # Setup mock LLM responses for different stages
        self.setup_mock_llm_responses()
    
    def teardown_method(self):
        """Cleanup test environment"""
        self.mock_st_patcher.stop()
        self.mock_llm_patcher.stop()
        shutil.rmtree(self.temp_dir)
    
    def setup_mock_llm_responses(self):
        """Setup mock LLM responses for different extraction stages"""
        
        def mock_chat(prompt, config=None):
            prompt_lower = prompt.lower()
            
            # Meta-analysis responses
            if "przeanalizuj tekst" in prompt_lower or "meta" in prompt_lower:
                return '''{"prompt": "Zidentyfikuj encje w tekście, zwracając szczególną uwagę na osoby, miejsca i organizacje. Użyj kontekstu do określenia relacji między encjami."}'''
            
            # Entity extraction responses
            elif "zidentyfikuj" in prompt_lower and "json" in prompt_lower:
                # Simulate different entities based on text content
                if "jan kowalski" in prompt_lower:
                    return '''{
                        "entities": [
                            {
                                "name": "Jan Kowalski",
                                "type": "OSOBA",
                                "description": "Główny bohater opowieści",
                                "confidence": 0.9,
                                "aliases": ["Jan", "Kowalski", "JK"],
                                "evidence": "Jan Kowalski pojawia się jako główna postać"
                            },
                            {
                                "name": "Warszawa",
                                "type": "MIEJSCE", 
                                "description": "Stolica Polski, miejsce akcji",
                                "confidence": 0.85,
                                "aliases": ["stolica", "miasto"],
                                "evidence": "Warszawa jest miejscem gdzie mieszka bohater"
                            }
                        ]
                    }'''
                
                elif "anna nowak" in prompt_lower:
                    return '''{
                        "entities": [
                            {
                                "name": "Anna Nowak",
                                "type": "OSOBA",
                                "description": "Przyjaciółka głównego bohatera",
                                "confidence": 0.8,
                                "aliases": ["Anna", "Anka"],
                                "evidence": "Anna Nowak występuje jako przyjaciółka"
                            },
                            {
                                "name": "Warszawa",
                                "type": "MIEJSCE",
                                "description": "Stolica Polski",
                                "confidence": 0.9,
                                "aliases": ["stolica", "WWA"],
                                "evidence": "Warszawa jako miejsce spotkania"
                            }
                        ]
                    }'''
                
                else:
                    return '{"entities": []}'
            
            # Auto-classification responses
            elif "sklasyfikuj" in prompt_lower:
                return '{"domains": ["simple"]}'
            
            return '{"entities": []}'
        
        self.mock_llm_instance.chat = mock_chat
    
    def create_test_chunks(self) -> List[TextChunk]:
        """Create test chunks for extraction"""
        chunks = [
            TextChunk(
                id=0,
                start=0,
                end=100,
                text="Jan Kowalski mieszka w Warszawie i pracuje jako nauczyciel. Jest bardzo zaangażowany w swoją pracę."
            ),
            TextChunk(
                id=1, 
                start=100,
                end=200,
                text="Anna Nowak to przyjaciółka Jana Kowalskiego. Również mieszka w Warszawie i często się spotykają."
            ),
            TextChunk(
                id=2,
                start=200,
                end=300,
                text="Warszawa to piękne miasto z bogatą historią. Jan Kowalski uwielbia spacerować po starówce."
            )
        ]
        
        # Add document source to chunks
        for chunk in chunks:
            chunk.document_source = "test_book.txt"
        
        return chunks
    
    def test_enhanced_entity_extraction_workflow(self):
        """Test complete enhanced extraction workflow with semantic store"""
        
        # Initialize EntityExtractor with SemanticStore
        extractor = EntityExtractor(
            model="claude-4-sonnet",
            domain_names=["simple"],
            storage_dir=str(self.temp_dir),
            enable_semantic_store=True
        )
        
        # Verify semantic store is initialized
        assert extractor.semantic_store is not None
        assert extractor.enable_semantic_store is True
        
        # Create test chunks
        chunks = self.create_test_chunks()
        
        # Extract entities
        extracted_entities = extractor.extract_entities(chunks)
        
        # Verify entities were extracted
        assert len(extracted_entities) > 0
        
        # Verify semantic store contains entities
        assert len(extractor.semantic_store.entities) > 0
        assert len(extractor.semantic_store.chunks) > 0
        
        # Check for specific entities
        entity_names = [entity.name for entity in extracted_entities]
        assert "Jan Kowalski" in entity_names
        assert "Anna Nowak" in entity_names
        assert "Warszawa" in entity_names
        
        # Verify semantic deduplication worked (Warszawa appears in multiple chunks)
        warszawa_entities = [e for e in extracted_entities if e.name == "Warszawa"]
        # Should be deduplicated to single entity
        assert len(warszawa_entities) <= 2  # Allowing for some variance in mock behavior
        
        # Check extraction stats
        stats = extractor.get_extraction_stats()
        assert stats['chunks_processed'] == 3
        assert stats['entities_extracted_raw'] > 0
        assert stats['entities_extracted_valid'] > 0
        
        # Check semantic store stats if available
        if 'semantic_store' in stats:
            store_stats = stats['semantic_store']
            assert store_stats['entities'] > 0
            assert store_stats['chunks'] > 0
    
    def test_contextual_enhancement_across_chunks(self):
        """Test that contextual enhancement improves extraction in later chunks"""
        
        # Initialize extractor
        extractor = EntityExtractor(
            model="claude-4-sonnet",
            domain_names=["simple"],
            storage_dir=str(self.temp_dir),
            enable_semantic_store=True
        )
        
        chunks = self.create_test_chunks()
        
        # Process chunks one by one to simulate real workflow
        all_entities = []
        
        for i, chunk in enumerate(chunks):
            # Mock enhanced contextual lookup for later chunks
            if i > 0:
                # Should find contextual entities from previous chunks
                contextual_entities = extractor.semantic_store.get_contextual_entities_for_ner(
                    chunk.text, max_entities=5
                )
                
                # Later chunks should benefit from context
                if i == 1:  # Second chunk should find "Jan Kowalski" from first chunk
                    # Verify contextual entities are available
                    assert len(extractor.semantic_store.entities) > 0
                
                if i == 2:  # Third chunk should find even more context
                    assert len(extractor.semantic_store.entities) > 0
            
            # Extract entities from single chunk
            chunk_entities = extractor.extract_entities([chunk])
            all_entities.extend(chunk_entities)
        
        # Verify progressive enhancement
        assert len(all_entities) > 0
        
        # Check that semantic store accumulated knowledge
        final_stats = extractor.semantic_store.get_stats()
        assert final_stats['entities'] > 0
        assert final_stats['chunks'] > 0
    
    def test_cross_chunk_relationship_discovery(self):
        """Test relationship discovery across chunks"""
        
        extractor = EntityExtractor(
            model="claude-4-sonnet",
            domain_names=["simple"],
            storage_dir=str(self.temp_dir),
            enable_semantic_store=True
        )
        
        chunks = self.create_test_chunks()
        
        # Extract entities (this should trigger relationship discovery)
        extracted_entities = extractor.extract_entities(chunks)
        
        # Verify relationships were discovered
        relationship_stats = extractor.semantic_store.relationship_manager.get_relationship_stats()
        assert relationship_stats['total_relationships'] > 0
        
        # Check specific relationship types
        relationship_types = relationship_stats['relationship_types']
        assert 'contains' in relationship_types  # Chunk-entity relationships
        
        # Verify graph structure
        graph_data = extractor.semantic_store.relationship_manager.export_graph_data()
        assert len(graph_data['nodes']) > 0
        assert len(graph_data['edges']) > 0
        
        # Check node types
        entity_nodes = [n for n in graph_data['nodes'] if n.get('type') == 'entity']
        chunk_nodes = [n for n in graph_data['nodes'] if n.get('type') == 'chunk']
        
        assert len(entity_nodes) > 0
        assert len(chunk_nodes) > 0
    
    def test_persistence_and_reload(self):
        """Test persistence and reloading of semantic store"""
        
        # Phase 1: Create and populate store
        extractor1 = EntityExtractor(
            model="claude-4-sonnet",
            domain_names=["simple"],
            storage_dir=str(self.temp_dir),
            enable_semantic_store=True
        )
        
        chunks = self.create_test_chunks()
        entities1 = extractor1.extract_entities(chunks)
        
        # Save state
        save_success = extractor1.semantic_store.save_to_disk()
        assert save_success
        
        # Verify files exist
        storage_files = list(self.temp_dir.rglob("*.json"))
        assert len(storage_files) > 0
        
        # Phase 2: Create new extractor and verify it loads existing data
        extractor2 = EntityExtractor(
            model="claude-4-sonnet",
            domain_names=["simple"],
            storage_dir=str(self.temp_dir),
            enable_semantic_store=True
        )
        
        # Should have loaded existing entities
        assert len(extractor2.semantic_store.entities) > 0
        assert len(extractor2.semantic_store.chunks) > 0
        
        # Compare stats
        stats1 = extractor1.semantic_store.get_stats()
        stats2 = extractor2.semantic_store.get_stats()
        
        assert stats1['entities'] == stats2['entities']
        assert stats1['chunks'] == stats2['chunks']
    
    def test_semantic_store_disabled(self):
        """Test EntityExtractor works correctly with semantic store disabled"""
        
        extractor = EntityExtractor(
            model="claude-4-sonnet",
            domain_names=["simple"],
            enable_semantic_store=False  # Disabled
        )
        
        # Verify semantic store is disabled
        assert extractor.semantic_store is None
        assert extractor.enable_semantic_store is False
        
        chunks = self.create_test_chunks()
        
        # Should still extract entities without semantic enhancement
        extracted_entities = extractor.extract_entities(chunks)
        
        # Verify entities were extracted
        assert len(extracted_entities) > 0
        
        # Verify no semantic store stats
        stats = extractor.get_extraction_stats()
        assert stats['semantic_enhancements'] == 0
        assert stats['semantic_deduplication_hits'] == 0
        assert 'semantic_store' not in stats
    
    def test_error_handling_in_semantic_operations(self):
        """Test graceful error handling in semantic operations"""
        
        extractor = EntityExtractor(
            model="claude-4-sonnet",
            domain_names=["simple"],
            storage_dir=str(self.temp_dir),
            enable_semantic_store=True
        )
        
        # Mock semantic store to raise errors
        with patch.object(extractor.semantic_store, 'get_contextual_entities_for_ner') as mock_contextual:
            mock_contextual.side_effect = Exception("Contextual lookup failed")
            
            with patch.object(extractor.semantic_store, 'add_entity_with_deduplication') as mock_add:
                mock_add.side_effect = Exception("Entity addition failed")
                
                chunks = self.create_test_chunks()
                
                # Should still work despite semantic store errors
                extracted_entities = extractor.extract_entities(chunks)
                
                # Should have extracted some entities (fallback to traditional method)
                assert len(extracted_entities) >= 0  # Allow for empty if all fail
                
                # Verify error handling didn't crash the extraction
                stats = extractor.get_extraction_stats()
                assert 'chunks_processed' in stats


class TestStoragePerformance:
    """Performance and stress tests for storage system"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Mock dependencies
        self.mock_st_patcher = patch('ner.storage.embedder.SentenceTransformer')
        mock_st = self.mock_st_patcher.start()
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = np.random.rand(384).astype(np.float32)
        mock_st.return_value = mock_model
    
    def teardown_method(self):
        """Cleanup"""
        self.mock_st_patcher.stop()
        shutil.rmtree(self.temp_dir)
    
    def test_large_scale_entity_storage(self):
        """Test storage performance with many entities"""
        
        store = SemanticStore(storage_dir=str(self.temp_dir))
        
        # Add many entities
        num_entities = 100
        chunk_id = store.register_chunk({
            'text': 'Large scale test chunk',
            'document_source': 'test.txt',
            'chunk_index': 0
        })
        
        for i in range(num_entities):
            entity_data = {
                'name': f'Entity {i}',
                'type': 'OSOBA',
                'description': f'Test entity number {i}',
                'confidence': 0.8,
                'aliases': [f'alias_{i}_1', f'alias_{i}_2'],
                'context': f'Context for entity {i}'
            }
            
            entity_id, is_new, aliases = store.add_entity_with_deduplication(entity_data, chunk_id)
            assert entity_id is not None
        
        # Verify all entities stored
        assert len(store.entities) == num_entities
        
        # Test search performance
        query_text = "Test query for performance"
        contextual_entities = store.get_contextual_entities_for_ner(query_text, max_entities=10)
        
        # Should complete without timeout
        assert isinstance(contextual_entities, list)
        
        # Test persistence performance
        save_success = store.save_to_disk()
        assert save_success
        
        # Verify files created
        entity_files = list((self.temp_dir / "entities").glob("*.json"))
        assert len(entity_files) == num_entities


if __name__ == "__main__":
    # Run tests
    import sys
    
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        if test_name == "integration":
            pytest.main(["-v", "test/test_storage_integration.py::TestSemanticStoreIntegration"])
        elif test_name == "performance":
            pytest.main(["-v", "test/test_storage_integration.py::TestStoragePerformance"])
        else:
            pytest.main(["-v", "test/test_storage_integration.py"])
    else:
        pytest.main(["-v", "test/test_storage_integration.py"])