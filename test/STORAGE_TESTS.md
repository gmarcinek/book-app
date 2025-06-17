# STORAGE_TESTS.md

**Dokumentacja uruchamiania testów storage - KISS version**

## **Quick Start**

```bash
# Wszystkie testy storage
poetry run python test/storage/run_storage_tests.py

# Live demo bez testów
poetry run python test/storage/demo_storage.py
```

## **Specific Test Suites**

```bash
# Podstawowe komponenty
poetry run python test/storage/run_storage_tests.py embedder    # EntityEmbedder  
poetry run python test/storage/run_storage_tests.py faiss      # FAISS Manager
poetry run python test/storage/run_storage_tests.py store      # SemanticStore

# Integracja z EntityExtractor
poetry run python test/storage/run_storage_tests.py integration

# Specific workflow tests
poetry run python test/storage/run_storage_tests.py workflow    # Enhanced extraction
poetry run python test/storage/run_storage_tests.py performance # Stress tests

# Quiet mode
poetry run python test/storage/run_storage_tests.py all -q
```

## **Direct pytest**

```bash
# Wszystkie testy
poetry run pytest test/storage/ -v

# Specific files
poetry run pytest test/storage/test_storage_basic.py -v
poetry run pytest test/storage/test_storage_integration.py -v

# Specific test methods
poetry run pytest test/storage/test_storage_basic.py::TestEntityEmbedder::test_generate_entity_embeddings -v
```

## **Co testujemy**

- **embedder** → dual embeddings, similarity, caching
- **faiss** → FAISS indices, search, add/remove operations  
- **store** → SemanticStore core functionality
- **integration** → full workflow z EntityExtractor
- **workflow** → 3-phase semantic enhancement
- **performance** → stress test z wieloma encjami

## **Requirements**

```bash
# Already in pyproject.toml
faiss-cpu = "^1.11.0"
networkx = "^3.5"  
sentence-transformers = "^2.2.2"
pytest = "^8.0.0"  # for testing
```

## **Demo**

```bash
# Live demo showing:
# - Entity addition & deduplication
# - Contextual entity discovery  
# - Known aliases lookup
# - Cross-chunk relationships
# - Persistence operations
poetry run python test/storage/demo_storage.py
```

**Note:** Wszystkie testy używają mock'ów - nie potrzeba API keys ani internetu.