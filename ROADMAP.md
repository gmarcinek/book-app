# Refactoring Entity Extraction: Od Single-Pass do Two-Pass z Real IDs

## 1. CO MA BYĆ ZROBIONE

### Obecny system (Single-Pass):
```
Chunk → LLM → [Entities + Relationships] → Real-time deduplication → Storage
```

### Docelowy system (Two-Pass):
```
Chunk → LLM → Entities → Real IDs → Storage → LLM → Relationships → Storage → Batch deduplication
```

**Konkretne zmiany:**
1. **Rozdzielenie extraction na 2 osobne LLM calls**
2. **Entities dostają real IDs przed relationship extraction**
3. **Relationships używają real IDs zamiast name resolution**
4. **Batch deduplication na końcu zamiast real-time**
5. **Contextual entities w relationship prompts mają real IDs**

## 2. DLACZEGO MA BYĆ ZROBIONE

### Problem #1: Zepsute relationships przez deduplikację
**Obecny flow:**
```python
# LLM zwraca: "Jan IS_IN dom"
entities = extract_entities(chunk)  # Jan, dom
deduplicated = dedupe(entities)     # Jan → merged z "Jan Kowalski" 
relationships = parse_relationships(response)  # ❌ "Jan" nie istnieje już!
```

**Efekt:** Relationships wskazują na nieistniejące entity names, bo deduplikacja zmieniła nazwy.

### Problem #2: Utrata kontekstu językowego
**Obecny problem:**
```python
# LLM dostaje description[:150] ← TYLKO 150 ZNAKÓW!
contextual_info = f"- {name}: {description[:100]}..."  # ← JESZCZE MNIEJ!
```

**Efekt:** LLM traci 80% kontekstu semantycznego potrzebnego do znalezienia relationships.

### Problem #3: Brak cross-chunk relationships
**Obecny problem:**
- Contextual entities nie mają IDs
- LLM nie może utworzyć relationship między chunk entity a contextual entity
- Tracone są connections między chunkami

### Problem #4: Race conditions w real-time deduplikacji
**Obecny problem:**
```python
# Chunk 1: tworzy "Jan" 
# Chunk 2: tworzy "Jan Kowalski" → dedupe → merge
# Chunk 3: relationship "Jan IS_IN dom" ❌ "Jan" już nie istnieje
```

## 3. JAKIMI KROKAMI MA BYĆ ZROBIONE

### KROK 1: Rozdzielenie promptów
**Plik:** `ner/domains/literary/literary.py`  
**Co:** Dodać nową metodę `get_relationships_extraction_prompt()`

```python
def get_relationships_extraction_prompt(self, chunk_text: str, 
                                      chunk_entities: List[dict], 
                                      contextual_entities: List[dict]) -> str:
    """
    chunk_entities: [{'id': 'ent.123.abc', 'name': 'Jan', 'type': 'CHARACTER'}, ...]
    contextual_entities: [{'id': 'ent.789.xyz', 'name': 'Maria', 'type': 'CHARACTER'}, ...]
    """
```

**Dlaczego:** LLM potrzebuje osobny, skoncentrowany prompt dla relationships z real IDs.

### KROK 2: Modyfikacja contextual entities
**Plik:** `ner/storage/store.py`  
**Co:** Rozszerzyć `get_contextual_entities_for_ner()` o parametr `full_context`

```python
def get_contextual_entities_for_ner(self, chunk_text: str, max_entities: int = 10, 
                                   threshold: float = None, full_context: bool = False):
    if full_context:
        # Dla relationships - PEŁNY kontekst
        contextual_entities.append({
            'id': entity.id,                    # ← REAL ID!
            'name': entity.name,
            'type': entity.type,
            'aliases': entity.aliases,          # ← WSZYSTKIE aliases
            'description': entity.description,  # ← PEŁNY description!
            'confidence': entity.confidence
        })
```

**Dlaczego:** Relationships potrzebują pełnego kontekstu semantycznego, nie 150 znaków.

### KROK 3: Nowy relationship extractor
**Plik:** `ner/extractor/relationship_extraction.py` (NOWY)  
**Co:** Dedykowany moduł dla relationship extraction

```python
class RelationshipExtractor:
    def extract_relationships_from_chunk(self, chunk: TextChunk, 
                                       chunk_entity_ids: List[str],
                                       semantic_store) -> List[dict]:
        # 1. Pobranie chunk entities z real IDs
        # 2. Pobranie contextual entities z full_context=True
        # 3. Budowanie relationship prompt z real IDs
        # 4. LLM call
        # 5. Parsing i validation
```

**Dlaczego:** Separation of concerns - entities i relationships to różne zadania wymagające różnych promptów.

### KROK 4: Modyfikacja głównego flow
**Plik:** `ner/extractor/base.py`  
**Co:** Zmiana `extract_entities()` na two-pass

```python
def extract_entities(self, chunks: List[TextChunk]) -> List[ExtractedEntity]:
    for chunk in chunks:
        # PASS 1: Entity extraction + immediate storage
        entities = extract_entities_from_chunk_multi_domain(...)
        entity_ids = clusterer.batch_cluster_chunk_entities(entities, chunk_id)
        self.semantic_store.persist_chunk_with_entities(chunk_id, entity_ids)
        
        # PASS 2: Relationship extraction (z real IDs!)
        relationship_extractor = RelationshipExtractor()
        relationships = relationship_extractor.extract_relationships_from_chunk(
            chunk, entity_ids, self.semantic_store
        )
        self.semantic_store.store_relationships(relationships)
    
    # PASS 3: Batch deduplication na końcu
    self.semantic_store.batch_deduplicate_entities()
```

**Dlaczego:** Entities muszą mieć real IDs przed relationship extraction.

### KROK 5: Wyłączenie real-time deduplikacji
**Plik:** `ner/extractor/batch_clustering.py`  
**Co:** Dodać flag `defer_deduplication=True`

```python
def batch_cluster_chunk_entities(self, entities, chunk_id, defer_deduplication=False):
    if defer_deduplication:
        # Nie rób similarity search - po prostu stwórz nowe entities
        return [self._create_new_entity(entity, chunk_id) for entity in entities]
    else:
        # Obecna logika z clustering
```

**Dlaczego:** Real-time deduplikacja psuje relationships przez zmianę entity names/IDs.

## DLACZEGO PRZEJŚCIE JEST SŁUSZNE

### Benefit #1: Zachowane relationships
**Przed:** 40% relationships zepsutych przez deduplikację  
**Po:** 100% relationships z valid IDs

### Benefit #2: Bogszy kontekst semantyczny
**Przed:** 150 znaków description → brakuje kontekstu  
**Po:** Pełny description + real IDs → cross-chunk relationships

### Benefit #3: Lepsza architektura
**Przed:** Monolityczny prompt (entities + relationships)  
**Po:** Focused prompts - każdy robi jedną rzecz dobrze

### Benefit #4: Deterministic results
**Przed:** Race conditions w real-time deduplikacji  
**Po:** Batch processing → consistent results

### Benefit #5: Easier debugging
**Przed:** Entities i relationships mixed w jednym response  
**Po:** Osobne outputs → łatwiejsze debugowanie

## RYZYKO I MITYGACJA

### Ryzyko: 2x więcej LLM calls
**Mitygacja:** Ale każdy call jest prostszy → potentially lepsze results + paralelizacja

### Ryzyko: Kompleksowość implementacji  
**Mitygacja:** Step-by-step approach - można rollback na każdym etapie

### Ryzyko: Storage overhead
**Mitygacja:** Batch deduplication na końcu → final storage size taki sam

**Bottom line:** Lepsze relationships są worth the complexity, bo relationships to klucz do knowledge graph value.

## PRAKTYCZNE PRZYKŁADY PRZED/PO

### Przykład: Chunk z entity merging

**PRZED (Single-Pass):**
```
INPUT CHUNK: "Jan Kowalski wszedł do swojego domu rodzinnego. Dom był stary."

LLM RESPONSE:
{
  "entities": [
    {"name": "Jan Kowalski", "type": "CHARACTER", "confidence": 0.9},
    {"name": "dom", "type": "LOCATION", "confidence": 0.8}
  ],
  "relationships": [
    {"source": "Jan Kowalski", "pattern": "IS_IN", "target": "dom"}
  ]
}

REAL-TIME DEDUPLICATION:
- "Jan Kowalski" merged z existing "Jan" → canonical name: "Jan"

RELATIONSHIP STORAGE:
❌ {"source": "Jan Kowalski", "target": "dom"} → BROKEN! "Jan Kowalski" nie istnieje
```

**PO (Two-Pass):**
```
PASS 1 - Entity Extraction:
INPUT: "Jan Kowalski wszedł do swojego domu rodzinnego. Dom był stary."
LLM RESPONSE: [{"name": "Jan Kowalski", "type": "CHARACTER"}, {"name": "dom", "type": "LOCATION"}]
STORAGE: ent.123.abc(Jan Kowalski), ent.456.def(dom) → real IDs nadane

PASS 2 - Relationship Extraction:
INPUT ENTITIES: 
- ent.123.abc (Jan Kowalski) - CHARACTER
- ent.456.def (dom) - LOCATION
INPUT CONTEXTUAL:
- ent.789.xyz (Maria) - CHARACTER: żona Jana, mieszka z nim
- ent.234.ghi (kuchnia) - LOCATION: pomieszczenie w domu Jana

LLM RESPONSE:
{
  "relationships": [
    {"source": "ent.123.abc", "pattern": "IS_IN", "target": "ent.456.def"},
    {"source": "ent.123.abc", "pattern": "IS_MARRIED", "target": "ent.789.xyz"},
    {"source": "ent.456.def", "pattern": "CONTAINS", "target": "ent.234.ghi"}
  ]
}

BATCH DEDUPLICATION (na końcu):
- ent.123.abc merged z existing ent.999.xxx → canonical: ent.999.xxx
- UPDATE relationships: ent.123.abc → ent.999.xxx
✅ Relationships zachowane z valid IDs!
```

### Przykład: Contextual entities format

**PRZED:**
```python
contextual_entities = [
    {
        'name': 'Maria',
        'type': 'CHARACTER', 
        'description': 'Żona Jana Kowalskiego, mieszka w domu rodzinnym z mężem. Ma brązowe włosy i...'[:150],  # ← OBCIĘTE!
        'aliases': ['Maria', 'żona', 'pani'][:3]  # ← OBCIĘTE!
    }
]
# BRAK ID! Nie można utworzyć relationship chunk → contextual
```

**PO:**
```python
contextual_entities = semantic_store.get_contextual_entities_for_ner(
    chunk.text, full_context=True
)
# RESULT:
[
    {
        'id': 'ent.789.xyz',  # ← REAL ID!
        'name': 'Maria',
        'type': 'CHARACTER',
        'description': 'Żona Jana Kowalskiego, mieszka w domu rodzinnym z mężem. Ma brązowe włosy i pracuje jako nauczycielka w miejscowej szkole. Często gotuje obiady dla całej rodziny.',  # ← PEŁNY!
        'aliases': ['Maria', 'żona', 'pani', 'nauczycielka', 'mama']  # ← WSZYSTKIE!
    }
]
```

## KONKRETNE FORMATY PROMPTÓW

### Entity Extraction Prompt (bez zmian):
```
Zidentyfikuj encje w tekście:

TEKST: "Jan wszedł do domu..."

JSON:
{
  "entities": [
    {"name": "Jan", "type": "CHARACTER", "description": "...", "confidence": 0.9}
  ]
}
```

### Relationship Extraction Prompt (NOWY):
```
Znajdź relationships w tekście używając podanych IDs:

TEKST: "Jan wszedł do domu rodzinnego. Maria czekała w kuchni."

ENCJE W TYM CHUNKU:
- ent.123.abc (Jan) - CHARACTER: Główny bohater, mężczyzna w średnim wieku
- ent.456.def (dom) - LOCATION: Dom rodzinny Jana, stary budynek

ZNANE ENCJE Z KONTEKSTU:
- ent.789.xyz (Maria) - CHARACTER: Żona Jana, mieszka z nim w domu rodzinnym
- ent.234.ghi (kuchnia) - LOCATION: Pomieszczenie w domu, miejsce gotowania

DOSTĘPNE PATTERNS: IS_IN, HAS, OWNS, IS_MARRIED, CONTAINS, BEFORE, AFTER, WITH

ZASADY:
- Używaj TYLKO podanych IDs w source/target
- Możesz łączyć encje z chunka z encjami z kontekstu

JSON:
{
  "relationships": [
    {"source": "ent.123.abc", "pattern": "IS_IN", "target": "ent.456.def"},
    {"source": "ent.123.abc", "pattern": "IS_MARRIED", "target": "ent.789.xyz"},
    {"source": "ent.456.def", "pattern": "CONTAINS", "target": "ent.234.ghi"}
  ]
}
```

## DATA FLOW I STORAGE

### Storage Schema:
```python
# ENTITIES (niezmienione)
StoredEntity {
    id: "ent.123.abc",
    name: "Jan Kowalski", 
    type: "CHARACTER",
    description: "...",
    canonical_id: None  # ← NOWE: po batch dedupe wskazuje na canonical
}

# RELATIONSHIPS (rozszerzone)
EntityRelationship {
    source_id: "ent.123.abc",
    target_id: "ent.456.def", 
    relation_type: "IS_IN",
    confidence: 0.9,
    chunk_id: "chunk.123",  # ← gdzie znalezione
    original_source_id: "ent.123.abc",  # ← backup przed dedupe update
    original_target_id: "ent.456.def"   # ← backup przed dedupe update
}
```

### Batch Deduplication Update Flow:
```python
def batch_deduplicate_entities():
    # 1. Znajdź clusters podobnych entities
    clusters = find_similar_entity_clusters()
    
    # 2. Merge każdy cluster → canonical entity
    canonical_mapping = {}  # old_id → canonical_id
    for cluster in clusters:
        canonical_id = merge_cluster(cluster)
        for old_id in cluster:
            canonical_mapping[old_id] = canonical_id
    
    # 3. Update wszystkich relationships
    for relationship in all_relationships:
        if relationship.source_id in canonical_mapping:
            relationship.source_id = canonical_mapping[relationship.source_id]
        if relationship.target_id in canonical_mapping:
            relationship.target_id = canonical_mapping[relationship.target_id]
    
    # 4. Update entities z canonical_id
    for entity_id, canonical_id in canonical_mapping.items():
        entities[entity_id].canonical_id = canonical_id
```

## EDGE CASES I HANDLING

### Edge Case 1: Brak contextual entities
```python
contextual_entities = semantic_store.get_contextual_entities_for_ner(chunk.text, full_context=True)
if not contextual_entities:
    # Relationship extraction tylko w obrębie chunka
    prompt = build_intra_chunk_relationship_prompt(chunk_entities)
```

### Edge Case 2: Invalid relationship IDs
```python
def validate_relationship(rel, all_entity_ids):
    if rel['source'] not in all_entity_ids:
        logger.warning(f"Invalid source ID: {rel['source']}")
        return False
    if rel['target'] not in all_entity_ids:
        logger.warning(f"Invalid target ID: {rel['target']}")
        return False
    return True
```

### Edge Case 3: Circular relationships
```python
def detect_circular_relationships(relationships):
    # Sprawdź czy A→B i B→A z tym samym pattern
    pairs = set()
    for rel in relationships:
        pair = (rel['source'], rel['target'], rel['pattern'])
        reverse_pair = (rel['target'], rel['source'], rel['pattern'])
        if reverse_pair in pairs:
            logger.warning(f"Circular relationship: {pair}")
        pairs.add(pair)
```

## TESTING STRATEGY

### Metryki do porównania PRZED/PO:
```python
def compare_extraction_quality():
    metrics = {
        'entity_count': len(extracted_entities),
        'relationship_count': len(extracted_relationships),
        'valid_relationships_ratio': valid_relationships / total_relationships,
        'cross_chunk_relationships': count_cross_chunk_relationships(),
        'duplicate_entities_before_dedupe': count_duplicates(),
        'entities_after_dedupe': len(canonical_entities),
        'relationship_survival_rate': relationships_after_dedupe / relationships_before_dedupe
    }
```

### Test Cases:
1. **Single chunk** - basic entity + relationship extraction
2. **Multi chunk** - cross-chunk relationships via contextual entities  
3. **Heavy duplication** - many similar entities → batch dedupe effectiveness
4. **Complex relationships** - nested, multiple patterns per entity pair
5. **Large documents** - performance z dużą liczbą chunks

### Success Criteria:
- **Relationship survival rate > 95%** (vs current ~60%)
- **Cross-chunk relationships > 0** (vs current 0)
- **Total processing time < 2x current** (acceptable dla lepszej jakości)
- **No race conditions** (deterministic results)

**Bottom line:** Lepsze relationships są worth the complexity, bo relationships to klucz do knowledge graph value.