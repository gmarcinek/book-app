"""
ner/semantic/config.py

Centralized configuration for semantic processing and clustering
All thresholds, parameters and tunable values in one place - KISS approach
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class SemanticConfig:
    """
    Single source of truth for all semantic processing parameters
    DRY principle - no more scattered thresholds across files
    """
    
    # === SIMILARITY THRESHOLDS ===
    # Entity type-specific thresholds for weighted similarity
    entity_type_thresholds: Dict[str, float] = None
    
    # Base similarity threshold for initial candidate filtering
    base_similarity_threshold: float = 0.3
    
    # === SEARCH THRESHOLDS ===
    # Name-based entity search (exact matching)
    name_search_threshold: float = 0.8
    name_search_max_results: int = 10
    
    # Context-based entity search (semantic discovery)
    context_search_threshold: float = 0.6
    context_search_max_results: int = 20
    
    # Contextual entities for NER enhancement
    contextual_entities_threshold: float = 0.6
    contextual_entities_max_results: int = 10
    
    # === COOCCURRENCE PARAMETERS ===
    # Minimum shared chunks ratio for co-occurrence relationships
    cooccurrence_threshold: float = 0.2
    
    # === CLUSTERING PARAMETERS ===
    # Content overlap bonus for weighted similarity
    max_content_overlap_bonus: float = 0.1
    
    def __post_init__(self):
        """Initialize default entity type thresholds if not provided"""
        if self.entity_type_thresholds is None:
            self.entity_type_thresholds = {
                # === SIMPLE DOMAIN (stare nazwy) ===
                'OSOBA': 0.75,           # Names are distinctive
                'ORGANIZACJA': 0.70,     # Organization names quite distinctive  
                'MIEJSCE': 0.65,         # Places can be ambiguous
                'PRZEDMIOT': 0.55,       # Objects often have generic names
                'KONCEPCJA': 0.50,       # Concepts are often similar
                'WYDARZENIE': 0.60,      # Events need decent threshold
                
                # === LITERARY DOMAIN (nowe nazwy) - WYŻSZE PROGI ===
                'CHARACTER': 0.75,       # Tak jak OSOBA - imiona są distinctive
                'LOCATION': 0.70,        # WYŻEJ niż MIEJSCE - nazwy miejsc powinny być różne
                'OBJECT': 0.65,          # WYŻEJ niż PRZEDMIOT - obiekty jak "fontanna" vs "domek" 
                'EMOTIONAL_STATE': 0.50, # Stany emocjonalne mogą być podobne
                'EVENT': 0.60,          # Wydarzenia potrzebują przyzwoitego progu
                'DIALOG': 0.40,          # Dialogi często się nakładają
                
                # === INNE TYPY ===
                'SCENA': 0.45,           # Scenes can be quite similar
                'default': 0.55          # Safe fallback
            }
    
    def get_threshold_for_type(self, entity_type: str) -> float:
        """Get similarity threshold for entity type"""
        return self.entity_type_thresholds.get(entity_type, self.entity_type_thresholds['default'])


# Global default instance - singleton pattern for simplicity
_default_config = None

def get_default_semantic_config() -> SemanticConfig:
    """Get default semantic configuration (singleton)"""
    global _default_config
    if _default_config is None:
        _default_config = SemanticConfig()
    return _default_config

def set_semantic_config(config: SemanticConfig):
    """Override default semantic configuration"""
    global _default_config
    _default_config = config