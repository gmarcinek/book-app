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