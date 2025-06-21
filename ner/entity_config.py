# ner/entity_config.py
"""
Entity and relationship configuration with Enums and centralized deduplication settings
Single source of truth for entity types, relationships and similarity thresholds
"""

from enum import Enum
from typing import Dict, List


# ===== ENTITY TYPES AS ENUM =====

class EntityType(Enum):
    """Standard entity types - keeping only what's currently used in DEFAULT_ENTITY_TYPES"""
    CHARACTER = "CHARACTER"
    EMOTIONAL_STATE = "EMOTIONAL_STATE"
    PHISICAL_STATE = "PHISICAL_STATE"  # Keep typo from original
    DESCRIPTION = "DESCRIPTION"
    LOCATION = "LOCATION"
    OBJECT = "OBJECT"
    EVENT = "EVENT"
    DIALOG = "DIALOG"
    TOOL = "TOOL"
    PROBLEM = "PROBLEM"
    CONCEPT = "CONCEPT"
    INSTITUTION = "INSTITUTION"
    TEMPORAL = "TEMPORAL"


# ===== RELATIONSHIP TYPES AS ENUM =====

class RelationType(Enum):
    """Standard relationship types"""
    # Structural relationships (from storage/models.py)
    CONTAINS = "contains"           # chunk contains entity
    SIMILAR_TO = "similar_to"      # entities are semantically similar
    
    # Domain relationship patterns
    IS_IN = "IS_IN"                # CHARACTER/OBJECT IS_IN LOCATION
    HAS = "HAS"                    # CHARACTER HAS OBJECT/EMOTIONAL_STATE
    OWNS = "OWNS"                  # CHARACTER OWNS OBJECT
    IS = "IS"                      # CHARACTER IS CHARACTER (rodzic/dziecko/małżonek)
    PERFORMS = "PERFORMS"          # CHARACTER PERFORMS EVENT
    PARTICIPATES = "PARTICIPATES"  # CHARACTER PARTICIPATES EVENT/DIALOG
    LIVES_IN = "LIVES_IN"          # CHARACTER LIVES_IN LOCATION
    BEFORE = "BEFORE"              # EVENT BEFORE EVENT
    AFTER = "AFTER"                # EVENT AFTER EVENT
    WITH = "WITH"                  # CHARACTER WITH CHARACTER
    IS_SIBLING = "IS_SIBLING"
    IS_PARENT = "IS_PARENT"
    IS_CHILD = "IS_CHILD"
    SIMILAR = "SIMILAR"


# ===== CENTRALIZED DEDUPLICATION CONFIGURATION =====

class DeduplicationConfig:
    """Centralized configuration for all deduplication thresholds"""
    
    # === ENTITY TYPE SIMILARITY THRESHOLDS ===
    ENTITY_SIMILARITY_THRESHOLDS = {
        # Literary domain - higher thresholds (more conservative)
        EntityType.CHARACTER: 0.75,       # Names are distinctive
        EntityType.LOCATION: 0.70,        # Place names should be different  
        EntityType.OBJECT: 0.65,          # Objects like "fountain" vs "house"
        EntityType.EMOTIONAL_STATE: 0.50, # Emotional states can be similar
        EntityType.EVENT: 0.60,           # Events need decent threshold
        EntityType.DIALOG: 0.40,          # Dialogs often overlap
        EntityType.DESCRIPTION: 0.55,     # Descriptions can be similar
        EntityType.PHISICAL_STATE: 0.55,  # Physical states
        EntityType.TOOL: 0.60,            # Tools should be distinct
        EntityType.PROBLEM: 0.55,         # Problems can be similar
        EntityType.CONCEPT: 0.50,         # Concepts often similar
        EntityType.INSTITUTION: 0.70,     # Institution names distinctive
        EntityType.TEMPORAL: 0.65,        # Time references
    }
    
    # === ENTITY TYPE WEIGHT FACTORS ===
    ENTITY_TYPE_WEIGHTS = {
        # Literary domain - type reliability weights
        EntityType.CHARACTER: 1.2,        # Imiona są bardzo distinctive  
        EntityType.LOCATION: 1.2,         # Nazwy lokacji mają być różne
        EntityType.OBJECT: 1.1,           # Obiekty powinny być distinctive
        EntityType.EMOTIONAL_STATE: 0.8,  # Stany emocjonalne często podobne
        EntityType.EVENT: 0.9,            # Wydarzenia umiarkowanie distinctive
        EntityType.DIALOG: 0.7,           # Dialogi często się nakładają
        EntityType.DESCRIPTION: 0.9,      # Opisy umiarkowanie distinctive
        EntityType.PHISICAL_STATE: 0.8,   # Stany fizyczne podobne
        EntityType.TOOL: 1.0,             # Narzędzia standardowo
        EntityType.PROBLEM: 0.8,          # Problemy często podobne
        EntityType.CONCEPT: 0.8,          # Koncepcje często podobne
        EntityType.INSTITUTION: 1.1,      # Organizacje distinctive
        EntityType.TEMPORAL: 1.0          # Czas standardowo
    }
    
    # === BASE SIMILARITY THRESHOLDS ===
    BASE_SIMILARITY_THRESHOLD = 0.3       # Initial filtering threshold
    
    # === SEARCH THRESHOLDS ===
    NAME_SEARCH_THRESHOLD = 0.8           # Exact name matching
    NAME_SEARCH_MAX_RESULTS = 10
    
    CONTEXT_SEARCH_THRESHOLD = 0.6        # Semantic discovery
    CONTEXT_SEARCH_MAX_RESULTS = 20
    
    CONTEXTUAL_ENTITIES_THRESHOLD = 0.6   # NER enhancement
    CONTEXTUAL_ENTITIES_MAX_RESULTS = 10
    
    # === COOCCURRENCE PARAMETERS ===
    COOCCURRENCE_THRESHOLD = 0.2          # Shared chunks ratio
    
    # === CLUSTERING PARAMETERS ===
    MAX_CONTENT_OVERLAP_BONUS = 0.1       # Weighted similarity bonus
    
    # === DOMAIN-SPECIFIC BASE THRESHOLDS ===
    DOMAIN_BASE_THRESHOLDS = {
        "literary": 0.3,
        "simple": 0.3, 
        "auto": 0.3
    }
    
    @classmethod
    def get_threshold_for_entity_type(cls, entity_type: EntityType) -> float:
        """Get similarity threshold for specific entity type"""
        return cls.ENTITY_SIMILARITY_THRESHOLDS.get(entity_type, 0.55)  # Default fallback
    
    @classmethod
    def get_threshold_for_entity_type_string(cls, entity_type_str: str) -> float:
        """Get threshold for entity type as string (backward compatibility)"""
        try:
            entity_type = EntityType(entity_type_str)
            return cls.get_threshold_for_entity_type(entity_type)
        except ValueError:
            return 0.55  # Default for unknown types
    
    @classmethod
    def get_type_weight(cls, entity_type_str: str) -> float:
        """Get type weight for entity type"""
        try:
            entity_type = EntityType(entity_type_str)
            return cls.ENTITY_TYPE_WEIGHTS.get(entity_type, 1.0)
        except ValueError:
            # Unknown type - default weight
            return 1.0
    
    @classmethod
    def get_domain_base_threshold(cls, domain_name: str) -> float:
        """Get base threshold for domain"""
        return cls.DOMAIN_BASE_THRESHOLDS.get(domain_name, 0.3)


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