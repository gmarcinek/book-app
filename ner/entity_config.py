# ner/entity_config.py
"""
Entity and relationship configuration - Default types and patterns
Domains can extend these defaults with their own specific types.
"""

from typing import List, Dict

# ===== DEFAULT ENTITY TYPES =====
DEFAULT_ENTITY_TYPES = [
    "CHARACTER",      # Playable character, NPC, człowiek z imienia, "jakiś typ", niedźwiedź w lesie
    "EMOTIONAL_STATE", # Stan emocjonalny wyrażony w tekście lub ekstrapolowany  
    "LOCATION",       # Miejsce gdzie podmiot jest i operuje, nie tylko wspomina
    "OBJECT",         # Istotne przedmioty: narzędzia, meble, coś do dotknięcia
    "EVENT",          # Wydarzenie z akcją i zmianą: wejście mamy, zatrzymanie zegara
    "DIALOG"          # Wymiana zdań, monolog, dialog wewnętrzny
]

# ===== DEFAULT RELATIONSHIP PATTERNS =====
DEFAULT_RELATIONSHIP_PATTERNS = [
    "IS_IN",          # CHARACTER/OBJECT IS_IN LOCATION
    "HAS",            # CHARACTER HAS OBJECT/EMOTIONAL_STATE
    "OWNS",           # CHARACTER OWNS OBJECT
    "IS",             # CHARACTER IS CHARACTER (rodzic/dziecko/małżonek)
    "PERFORMS",       # CHARACTER PERFORMS EVENT
    "PARTICIPATES",   # CHARACTER PARTICIPATES EVENT/DIALOG
    "LIVES_IN",       # CHARACTER LIVES_IN LOCATION
    "BEFORE",         # EVENT BEFORE EVENT
    "AFTER",          # EVENT AFTER EVENT
    "WITH"            # CHARACTER WITH CHARACTER (razem w scenie)
]

# ===== CORE RELATIONSHIP TYPES (from storage/models.py) =====
CORE_RELATIONSHIP_TYPES = [
    "contains",       # chunk contains entity (structural)
    "similar_to"      # entities are semantically similar
]

# ===== ALL AVAILABLE RELATIONSHIP TYPES =====
def get_all_relationship_types() -> List[str]:
    """Get all available relationship types combining core and default patterns"""
    return CORE_RELATIONSHIP_TYPES + DEFAULT_RELATIONSHIP_PATTERNS

# ===== DOMAIN EXTENSION HELPERS =====
def extend_entity_types(base_types: List[str], additional_types: List[str]) -> List[str]:
    """Extend base entity types with domain-specific types"""
    return list(set(base_types + additional_types))

def extend_relationship_patterns(base_patterns: List[str], additional_patterns: List[str]) -> List[str]:
    """Extend base relationship patterns with domain-specific patterns"""
    return list(set(base_patterns + additional_patterns))

# ===== CONFIDENCE THRESHOLDS =====
DEFAULT_CONFIDENCE_THRESHOLDS = {
    "entity_extraction": 0.3,
    "relationship_extraction": 0.5,
    "semantic_similarity": 0.7
}