#!/usr/bin/env python3
"""
test/demo_storage.py

Demo script showing basic SemanticStore operations
Demonstrates entity addition, deduplication, search, and persistence
"""

import sys
import tempfile
import shutil
from pathlib import Path

# Add root to path
sys.path.append(str(Path(__file__).parent.parent))

from ner.storage import SemanticStore


def demo_basic_operations():
    """Demonstrate basic storage operations"""
    print("🏗️ SemanticStore Demo - Basic Operations")
    print("=" * 50)
    
    # Create temporary storage
    temp_dir = tempfile.mkdtemp()
    print(f"📁 Using temporary storage: {temp_dir}")
    
    try:
        # Initialize store
        print("\n📦 Initializing SemanticStore...")
        store = SemanticStore(
            storage_dir=temp_dir,
            embedding_model="sentence-transformers/all-MiniLM-L6-v2"
        )
        print("✅ Store initialized")
        
        # Register chunks
        print("\n📝 Registering test chunks...")
        chunk1_id = store.register_chunk({
            'text': 'Jan Kowalski mieszka w Warszawie i pracuje jako nauczyciel.',
            'document_source': 'book1.txt',
            'chunk_index': 0
        })
        
        chunk2_id = store.register_chunk({
            'text': 'Anna Nowak to przyjaciółka Jana Kowalskiego. Również mieszka w Warszawie.',
            'document_source': 'book1.txt', 
            'chunk_index': 1
        })
        print(f"✅ Registered chunks: {chunk1_id}, {chunk2_id}")
        
        # Add entities
        print("\n👤 Adding entities...")
        
        # Entity 1: Jan Kowalski
        entity1_data = {
            'name': 'Jan Kowalski',
            'type': 'OSOBA',
            'description': 'Główny bohater książki, nauczyciel',
            'confidence': 0.9,
            'aliases': ['Jan', 'Kowalski'],
            'context': 'Jan Kowalski mieszka w Warszawie'
        }
        
        entity1_id, is_new1, aliases1 = store.add_entity_with_deduplication(entity1_data, chunk1_id)
        print(f"✅ Added entity: {entity1_id} (new: {is_new1})")
        
        # Entity 2: Warszawa
        entity2_data = {
            'name': 'Warszawa',
            'type': 'MIEJSCE',
            'description': 'Stolica Polski',
            'confidence': 0.85,
            'aliases': ['stolica'],
            'context': 'Warszawa to miasto gdzie mieszka Jan'
        }
        
        entity2_id, is_new2, aliases2 = store.add_entity_with_deduplication(entity2_data, chunk1_id)
        print(f"✅ Added entity: {entity2_id} (new: {is_new2})")
        
        # Entity 3: Anna Nowak
        entity3_data = {
            'name': 'Anna Nowak',
            'type': 'OSOBA',
            'description': 'Przyjaciółka Jana Kowalskiego',
            'confidence': 0.8,
            'aliases': ['Anna', 'Anka'],
            'context': 'Anna Nowak to przyjaciółka Jana'
        }
        
        entity3_id, is_new3, aliases3 = store.add_entity_with_deduplication(entity3_data, chunk2_id)
        print(f"✅ Added entity: {entity3_id} (new: {is_new3})")
        
        # Entity 4: Warszawa again (should be deduplicated)
        entity4_data = {
            'name': 'Warszawa',
            'type': 'MIEJSCE',
            'description': 'Stolica Polski, piękne miasto',
            'confidence': 0.9,  # Higher confidence
            'aliases': ['WWA', 'miasto'],  # New aliases
            'context': 'Warszawa gdzie mieszka Anna'
        }
        
        entity4_id, is_new4, aliases4 = store.add_entity_with_deduplication(entity4_data, chunk2_id)
        print(f"🔗 Deduplication test: {entity4_id} (new: {is_new4}, discovered aliases: {aliases4})")
        
        # Show store statistics
        print("\n📊 Store Statistics:")
        stats = store.get_stats()
        print(f"  Entities: {stats['entities']}")
        print(f"  Chunks: {stats['chunks']}")
        print(f"  FAISS entities: {stats['faiss']['entity_name_count']}")
        print(f"  Relationships: {stats['relationships']['total_relationships']}")
        
        # Test contextual entity discovery
        print("\n🎯 Testing contextual entity discovery...")
        query_text = "Gdzie mieszka nauczyciel? Czy zna jakieś osoby?"
        contextual_entities = store.get_contextual_entities_for_ner(query_text, max_entities=5)
        
        print(f"Found {len(contextual_entities)} contextual entities:")
        for entity in contextual_entities:
            print(f"  - {entity['name']} ({entity['type']}) [conf: {entity['confidence']:.2f}]")
            if entity['aliases']:
                print(f"    Aliases: {', '.join(entity['aliases'])}")
        
        # Test known aliases lookup
        print("\n🏷️ Testing known aliases lookup...")
        alias_query = "Jan mieszka w stolicy Polski"
        known_aliases = store.get_known_aliases_for_chunk(alias_query)
        
        print(f"Found {len(known_aliases)} entities with known aliases:")
        for name, aliases in known_aliases.items():
            print(f"  - {name}: {', '.join(aliases)}")
        
        # Persist chunks with entities
        print("\n💾 Persisting chunks with entities...")
        store.persist_chunk_with_entities(chunk1_id, [entity1_id, entity2_id])
        store.persist_chunk_with_entities(chunk2_id, [entity3_id, entity4_id])
        
        # Discover cross-chunk relationships
        print("\n🔗 Discovering cross-chunk relationships...")
        relationships_count = store.discover_cross_chunk_relationships()
        print(f"Discovered {relationships_count} cross-chunk relationships")
        
        # Save to disk
        print("\n💾 Saving store to disk...")
        save_success = store.save_to_disk()
        print(f"Save successful: {save_success}")
        
        # Show final statistics
        print("\n📈 Final Statistics:")
        final_stats = store.get_stats()
        print(f"  Total entities stored: {final_stats['entities']}")
        print(f"  Total chunks stored: {final_stats['chunks']}")
        print(f"  Total relationships: {final_stats['relationships']['total_relationships']}")
        print(f"  Storage size: {final_stats['storage']['total_size_mb']:.2f} MB")
        
        print("\n✅ Demo completed successfully!")
        
        # Show stored entities
        print("\n📋 Stored Entities:")
        for entity_id, entity in store.entities.items():
            print(f"  {entity.name} ({entity.type}) - conf: {entity.confidence:.2f}")
            if entity.aliases:
                print(f"    Aliases: {', '.join(entity.aliases)}")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up temporary storage: {temp_dir}")
        shutil.rmtree(temp_dir)


def demo_search_and_similarity():
    """Demonstrate search and similarity features"""
    print("\n🔍 SemanticStore Demo - Search & Similarity")
    print("=" * 50)
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        store = SemanticStore(storage_dir=temp_dir)
        
        # Add diverse entities for search testing
        chunk_id = store.register_chunk({
            'text': 'Various entities for search testing',
            'document_source': 'test.txt',
            'chunk_index': 0
        })
        
        entities_data = [
            {
                'name': 'Albert Einstein',
                'type': 'OSOBA',
                'description': 'Znany fizyk, twórca teorii względności',
                'confidence': 0.95,
                'aliases': ['Einstein', 'Albert'],
                'context': 'Albert Einstein był geniuszem fizyki'
            },
            {
                'name': 'Warszawa',
                'type': 'MIEJSCE',
                'description': 'Stolica Polski, centrum polityczne i kulturalne',
                'confidence': 0.9,
                'aliases': ['stolica', 'WWA'],
                'context': 'Warszawa to największe miasto Polski'
            },
            {
                'name': 'Teoria względności',
                'type': 'KONCEPCJA',
                'description': 'Fundamentalna teoria fizyki stworzona przez Einsteina',
                'confidence': 0.85,
                'aliases': ['relatywność', 'teoria Einsteina'],
                'context': 'Teoria względności zrewolucjonizowała fizykę'
            },
            {
                'name': 'Kraków',
                'type': 'MIEJSCE',
                'description': 'Historyczna stolica Polski',
                'confidence': 0.88,
                'aliases': ['dawna stolica', 'miasto królewskie'],
                'context': 'Kraków to piękne historyczne miasto'
            }
        ]
        
        # Add all entities
        entity_ids = []
        for entity_data in entities_data:
            entity_id, _, _ = store.add_entity_with_deduplication(entity_data, chunk_id)
            entity_ids.append(entity_id)
        
        print(f"✅ Added {len(entity_ids)} entities for search testing")
        
        # Test search by name similarity
        print("\n🔍 Testing search by name...")
        search_queries = [
            "fizyk",
            "miasto", 
            "Einstein",
            "stolica"
        ]
        
        for query in search_queries:
            print(f"\nQuery: '{query}'")
            results = store.search_entities_by_name(query, max_results=3)
            
            if results:
                for entity, similarity in results:
                    print(f"  {entity.name} ({entity.type}) - similarity: {similarity:.3f}")
            else:
                print("  No results found")
        
        print("\n✅ Search demo completed!")
        
    except Exception as e:
        print(f"❌ Search demo failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    print("🧪 SemanticStore Demonstration")
    print("Testing core functionality without full NER pipeline")
    print()
    
    try:
        # Check dependencies
        from ner.storage import SemanticStore
        import numpy as np
        import faiss
        import networkx as nx
        print("✅ All dependencies available")
        
        # Run demos
        demo_basic_operations()
        demo_search_and_similarity()
        
        print("\n🎉 All demos completed successfully!")
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Install with: pip install sentence-transformers faiss-cpu networkx numpy")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)