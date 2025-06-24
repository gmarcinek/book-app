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
    """Centralized configuration for all deduplication thresholds - SIMPLIFIED"""
    
    # === UNIFIED MERGE THRESHOLD ===
    MERGE_THRESHOLD = 0.30  # Single threshold for all merge decisions
    
    # === NON-MERGE THRESHOLDS (unchanged) ===
    BASE_SIMILARITY_THRESHOLD = 0.3       # Basic filtering
    NAME_SEARCH_THRESHOLD = 0.8           # User search
    NAME_SEARCH_MAX_RESULTS = 10
    CONTEXT_SEARCH_THRESHOLD = 0.6        # Context discovery
    CONTEXT_SEARCH_MAX_RESULTS = 20
    CONTEXTUAL_ENTITIES_THRESHOLD = 0.6   # NER enhancement
    CONTEXTUAL_ENTITIES_MAX_RESULTS = 10
    COOCCURRENCE_THRESHOLD = 0.2          # Shared chunks ratio
    MAX_CONTENT_OVERLAP_BONUS = 0.1       # Weighted similarity bonus
    
    @classmethod
    def get_merge_threshold(cls) -> float:
        """Get unified merge threshold for all entity types"""
        return cls.MERGE_THRESHOLD


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