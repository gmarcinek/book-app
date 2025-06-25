Scenariusz A: Deduplikacja na końcu całego pipeline
Obecny flow:
Text → Chunks → [Entity extraction + Relationship extraction + Deduplikacja] → Store → Graph
Nowy flow:
Text → Chunks → Entity extraction → Relationship extraction → Store RAW → Deduplikacja → Graph
Szczegółowy breakdown:
Krok 1: Entity Extraction

LLM dostaje chunk tekstu
Zwraca tylko entities (bez relationships)
Każda entity dostaje prawdziwe ID (nie temp)
Żadnej deduplikacji - wszystko ląduje w storage "as-is"
Duplikaty są OK i expected

Krok 2: Relationship Extraction

Osobny LLM call z tym samym chunkiem
LLM dostaje listę entities z prawdziwymi ID z kroku 1
Zwraca relationships używając tych ID
Żadnego name resolution - ID są już znane

Krok 3: Raw Storage

Wszystkie entities trafiają do SemanticStore
Wszystkie relationships trafiają do RelationshipManager
Duplikaty zostają - "Jan" i "Jan Kowalski" to osobne entities
FAISS indexuje wszystko bez clustering

Krok 4: Batch Deduplication

Na końcu całego procesu (wszystkie chunks processed)
EntityBatchClusterer analizuje wszystkie entities naraz
Tworzy clusters podobnych entities
EntityMerger merguje clusters w canonical entities
Update relationships żeby pointowały na canonical entities

Krok 5: Graph Creation

Graph building używa deduplicated entities
Relationships już pointują na canonical entities
Clean graph bez duplikatów

Kluczowe różnice:
Co się zmienia:

2 LLM calls zamiast 1 per chunk
No real-time clustering during extraction
Batch processing deduplikacji na końcu
Preserved context dla relationships

Co zostaje:

Te same domeny i prompty
Ten sam EntityMerger i clustering logic
Te same storage komponenty
Ten sam final graph

Result:
Lepsze relationships (bo z original context) + ten sam final quality deduplikacji, ale z delayed timing.

Podział zadań dla Scenariusza A
Task 1: Rozdzielenie entity/relationship extraction
Scope: Modyfikacja LLM prompts i parsing logic
Files:

ner/domains/*/literary.py (i inne domeny)
ner/extractor/parsing.py
ner/extractor/extraction.py

Co:

Nowe prompty: tylko entities (bez relationships)
Nowy relationship extraction prompt
Nowy parsing dla relationship-only responses
Nowa funkcja extract_relationships_from_chunk()


Task 2: Wyłączenie real-time deduplikacji
Scope: Disable clustering podczas extraction
Files:

ner/extractor/batch_clustering.py
ner/extractor/base.py
ner/storage/store.py

Co:

Flag defer_deduplication=True w EntityExtractor
EntityBatchClusterer skip clustering, direct store
Simple ID generation bez similarity checking


Task 3: Dedicated relationship extractor
Scope: Nowy moduł dla relationship extraction
Files:

ner/extractor/relationship_extractor.py (NEW)
ner/extractor/__init__.py

Co:

RelationshipExtractor class
Prompt building dla relationships
Entity ID → LLM prompt formatting
Relationship validation


Task 4: Batch deduplication system
Scope: Deduplikacja po zakończeniu extraction
Files:

ner/extractor/base.py (nowa faza)
ner/storage/clustering/batch_deduplicator.py (NEW)
ner/pipeline.py

Co:

BatchDeduplicator - orchestrator deduplikacji
Post-processing phase w EntityExtractor.extract_entities()
Relationship update po merge


Task 5: Storage adaptations
Scope: Support dla raw + deduplicated views
Files:

ner/storage/store.py
ner/storage/relations.py

Co:

Dual storage: raw entities + canonical mapping
Relationship updates po deduplikacji
Query methods: get_entities(deduplicated=True/False)


Kolejność implementacji:
Phase 1: Core extraction split

Task 1 (prompts + parsing)
Task 3 (relationship extractor)
Validation że 2-step działa

Phase 2: Deduplication refactor

Task 2 (disable real-time clustering)
Task 4 (batch deduplication)
Integration testing

Phase 3: Storage enhancements

Task 5 (dual views)
End-to-end testing
Performance optimization