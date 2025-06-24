# ner/entity_config.py
"""
Entity and relationship configuration with Enums and centralized deduplication settings
Single source of truth for entity types, relationships and similarity thresholds
"""

from enum import Enum
from typing import Dict, List, Any


# ===== ENTITY TYPES AS ENUM =====

class EntityType(Enum):
    """Standard entity types - keeping only what's currently used in DEFAULT_ENTITY_TYPES"""
    CHARACTER = "CHARACTER"
    EMOTIONAL_STATE = "EMOTIONAL_STATE"
    PHISICAL_STATE = "PHISICAL_STATE"
    DESCRIPTION = "DESCRIPTION"
    LOCATION = "LOCATION"
    ADDRESS = "ADDRESS"
    OBJECT = "OBJECT"
    EVENT = "EVENT"
    DIALOG = "DIALOG"
    TOOL = "TOOL"
    PROBLEM = "PROBLEM"
    CONCEPT = "CONCEPT"
    INSTITUTION = "INSTITUTION"
    DATE = "DATE"


# ===== RELATIONSHIP TYPES AS ENUM =====

class RelationType(Enum):
    """Standard relationship types"""
    # Structural relationships (from storage/models.py)
    CONTAINS = "contains"           # chunk contains entity
    SIMILAR_TO = "similar_to"      # entities are semantically similar
    
    # Domain relationship patterns
    IS_IN = "IS_IN"
    HAS = "HAS"
    OWNS = "OWNS"
    IS = "IS"
    PERFORMS = "PERFORMS"
    PARTICIPATES = "PARTICIPATES"
    LIVES_IN = "LIVES_IN"
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    WITH = "WITH"
    IS_SIBLING = "IS_SIBLING"
    IS_PARENT = "IS_PARENT"
    IS_CHILD = "IS_CHILD"
    SIMILAR = "SIMILAR"


# ===== CENTRALIZED DEDUPLICATION CONFIGURATION =====

class DeduplicationConfig:
    """Centralized configuration for all deduplication thresholds and similarity parameters"""
    
    # === UNIFIED MERGE THRESHOLD ===
    MERGE_THRESHOLD = 0.60  # Single threshold for all merge decisions
    TYPE_MERGE_THRESHOLDS = {
        EntityType.CHARACTER: 0.85,           # BARDZO wysokie - różne osoby
        EntityType.LOCATION: 0.70,            # Wysokie - różne miejsca
        EntityType.ADDRESS: 0.80,             # Bardzo wysokie - precyzyjne adresy  
        EntityType.INSTITUTION: 0.75,        # Wysokie - różne organizacje
        EntityType.EVENT: 0.60,               # Średnie - wydarzenia
        EntityType.OBJECT: 0.50,              # Niższe - obiekty
        EntityType.TOOL: 0.55,                # Średnie-niskie
        EntityType.CONCEPT: 0.45,             # Najniższe - abstrakcyjne
        EntityType.PROBLEM: 0.50,             # Średnie-niskie
        EntityType.DIALOG: 0.40,              # Niskie - dialogi podobne
        EntityType.EMOTIONAL_STATE: 0.45,    # Niskie - stany emocjonalne
        EntityType.PHISICAL_STATE: 0.50,     # Średnie-niskie
        EntityType.DESCRIPTION: 0.45,        # Niskie - opisy podobne
        EntityType.DATE: 0.90,                # BARDZO wysokie - precyzyjne daty
    }
    
    # === MULTI-COMPONENT SIMILARITY WEIGHTS ===
    COMPONENT_WEIGHTS = {
        EntityType.CHARACTER: {
            "name": 0.60,        # Names są kluczowe dla osób
            "description": 0.25, # Opisy mogą być podobne (LLM generuje)
            "context": 0.15      # Kontekst pomocny ale nie decydujący
        },
        EntityType.LOCATION: {
            "name": 0.70,        # Nazwy miejsc są najważniejsze
            "description": 0.20, # Opisy miejsc mogą się różnić
            "context": 0.10      # Gdzie miejsce wystąpiło
        },
        EntityType.ADDRESS: {
            "name": 0.80,        # Adresy muszą być precyzyjne
            "description": 0.15, # Opisy adresów mniej ważne
            "context": 0.05      # Kontekst nieistotny
        },
        EntityType.INSTITUTION: {
            "name": 0.65,        # Nazwy firm/organizacji ważne
            "description": 0.25, # Opisy mogą być różne
            "context": 0.10      # Kontekst umiarkowanie ważny
        },
        EntityType.OBJECT: {
            "name": 0.50,        # Nazwy obiektów mogą być różne
            "description": 0.40, # Opisy obiektów istotne
            "context": 0.10      # Gdzie obiekt wystąpił
        },
        EntityType.TOOL: {
            "name": 0.55,        # Nazwy narzędzi ważne
            "description": 0.35, # Opisy funkcjonalności
            "context": 0.10      # Kontekst użycia
        },
        EntityType.CONCEPT: {
            "name": 0.30,        # Koncepcje mogą mieć różne nazwy
            "description": 0.60, # Znaczenie najważniejsze
            "context": 0.10      # Kontekst pomocny
        },
        EntityType.PROBLEM: {
            "name": 0.40,        # Nazwy problemów mogą być różne
            "description": 0.50, # Opisy problemów kluczowe
            "context": 0.10      # Kontekst wystąpienia
        },
        EntityType.EVENT: {
            "name": 0.55,        # Nazwy wydarzeń ważne
            "description": 0.35, # Opisy wydarzeń istotne
            "context": 0.10      # Kiedy/gdzie wystąpiło
        },
        EntityType.DIALOG: {
            "name": 0.30,        # Nazwy dialogów mniej ważne
            "description": 0.60, # Treść dialogu najważniejsza
            "context": 0.10      # Kontekst rozmowy
        },
        EntityType.EMOTIONAL_STATE: {
            "name": 0.40,        # Nazwy stanów emocjonalnych
            "description": 0.50, # Opisy stanów ważne
            "context": 0.10      # Kontekst wystąpienia
        },
        EntityType.PHISICAL_STATE: {
            "name": 0.45,        # Nazwy stanów fizycznych
            "description": 0.45, # Opisy stanów równie ważne
            "context": 0.10      # Kontekst wystąpienia
        },
        EntityType.DESCRIPTION: {
            "name": 0.35,        # Nazwy opisów
            "description": 0.55, # Treść opisu najważniejsza
            "context": 0.10      # Kontekst opisu
        },
        EntityType.DATE: {
            "name": 0.85,        # Nazwy dat bardzo ważne (precyzja)
            "description": 0.10, # Opisy dat mniej istotne
            "context": 0.05      # Kontekst wystąpienia
        }
    }
    
    # === DEFAULT WEIGHTS FOR UNKNOWN TYPES ===
    DEFAULT_COMPONENT_WEIGHTS = {
        "name": 0.50,
        "description": 0.40,
        "context": 0.10
    }
    
    # === STABILITY WEIGHT CONFIGURATION ===
    STABILITY_CONFIG = {
        "no_sources_weight": 0.8,        # Weight when entity has no source chunks
        "single_source_weight": 0.9,     # Weight for 1 source chunk
        "max_weight": 1.0,                # Maximum weight for 3+ source chunks
        "increment_per_source": 0.05      # Weight increase per additional source
    }
    
    # === CONFIDENCE WEIGHT CONFIGURATION ===
    CONFIDENCE_CONFIG = {
        "base_weight": 0.8,       # Minimum confidence weight
        "max_boost": 0.2,         # Maximum additional weight from confidence
        "scale_factor": 0.2       # How much confidence affects final weight
    }
    
    # === CONTENT OVERLAP CONFIGURATION ===
    CONTENT_OVERLAP_CONFIG = {
        "min_word_length": 2,           # Minimum word length for overlap calculation
        "max_bonus": 0.1,               # Maximum bonus from content overlap
        "overlap_multiplier": 0.4       # Multiplier for overlap ratio
    }
    
    # === SIMILARITY DEBUG CONFIGURATION ===
    SIMILARITY_DEBUG_CONFIG = {
        "show_component_breakdown": True,     # Show name/desc/context similarities
        "show_weights": True,                 # Show component weights
        "max_description_length": 80,        # Max chars to show in debug
        "show_semantic_text": True,          # Show full semantic text
        "show_separator": True,              # Show separator lines
        "separator_length": 80               # Length of separator lines
    }
    
    # === NON-MERGE THRESHOLDS ===
    BASE_SIMILARITY_THRESHOLD = 0.3       # Basic filtering
    NAME_SEARCH_THRESHOLD = 0.8           # User search
    NAME_SEARCH_MAX_RESULTS = 10
    CONTEXT_SEARCH_THRESHOLD = 0.6        # Context discovery
    CONTEXT_SEARCH_MAX_RESULTS = 20
    CONTEXTUAL_ENTITIES_THRESHOLD = 0.6   # NER enhancement
    CONTEXTUAL_ENTITIES_MAX_RESULTS = 10
    COOCCURRENCE_THRESHOLD = 0.2          # Shared chunks ratio
    MAX_CONTENT_OVERLAP_BONUS = 0.1       # Weighted similarity bonus (deprecated, use CONTENT_OVERLAP_CONFIG)
    
    @classmethod
    def get_component_weights(cls, entity_type: str) -> Dict[str, float]:
        """Get component weights for specific entity type"""
        try:
            enum_type = EntityType(entity_type)
            return cls.COMPONENT_WEIGHTS.get(enum_type, cls.DEFAULT_COMPONENT_WEIGHTS)
        except ValueError:
            return cls.DEFAULT_COMPONENT_WEIGHTS
    
    @classmethod
    def get_stability_config(cls) -> Dict[str, float]:
        """Get stability weight configuration"""
        return cls.STABILITY_CONFIG
    
    @classmethod
    def get_confidence_config(cls) -> Dict[str, float]:
        """Get confidence weight configuration"""
        return cls.CONFIDENCE_CONFIG
    
    @classmethod
    def get_content_overlap_config(cls) -> Dict[str, float]:
        """Get content overlap configuration"""
        return cls.CONTENT_OVERLAP_CONFIG
    
    @classmethod
    def get_debug_config(cls) -> Dict[str, Any]:
        """Get similarity debug configuration"""
        return cls.SIMILARITY_DEBUG_CONFIG

# ===== BACKWARD COMPATIBILITY =====

# Convert enums to lists for existing code
DEFAULT_ENTITY_TYPES = [e.value for e in EntityType]
DEFAULT_RELATIONSHIP_PATTERNS = [r.value for r in RelationType if r not in [
    RelationType.CONTAINS, RelationType.SIMILAR_TO
]]
CORE_RELATIONSHIP_TYPES = [RelationType.CONTAINS.value, RelationType.SIMILAR_TO.value]

# Legacy confidence thresholds
DEFAULT_CONFIDENCE_THRESHOLDS = {
    "entity_extraction": 0.3,
    "relationship_extraction": 0.5,
    "semantic_similarity": 0.7
}


# ===== UTILITY FUNCTIONS =====

def get_all_relationship_types() -> List[str]:
    """Get all available relationship types"""
    return [r.value for r in RelationType]

def extend_entity_types(base_types: List[str], additional_types: List[str]) -> List[str]:
    """Extend base entity types with domain-specific types"""
    return list(set(base_types + additional_types))

def extend_relationship_patterns(base_patterns: List[str], additional_patterns: List[str]) -> List[str]:
    """Extend base relationship patterns with domain-specific patterns"""
    return list(set(base_patterns + additional_patterns))

