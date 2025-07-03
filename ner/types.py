# ner/types.py
"""
Basic entity and relationship types without deduplication logic
Clean enums for NER system - KISS principle
"""

from enum import Enum
from typing import List


class EntityType(Enum):
    """Standard entity types"""
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


class RelationType(Enum):
    """Standard relationship types"""
    # Core structural relationships
    CONTAINS = "contains"
    SIMILAR_TO = "similar_to"
    
    # Domain relationships
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


# Backward compatibility constants
DEFAULT_ENTITY_TYPES = [e.value for e in EntityType]

DEFAULT_RELATIONSHIP_PATTERNS = [r.value for r in RelationType if r not in [
    RelationType.CONTAINS, RelationType.SIMILAR_TO
]]

CORE_RELATIONSHIP_TYPES = [RelationType.CONTAINS.value, RelationType.SIMILAR_TO.value]


# Default confidence thresholds for extraction
DEFAULT_CONFIDENCE_THRESHOLDS = {
    "entity_extraction": 0.3,
    "relationship_extraction": 0.5,
    "semantic_similarity": 0.7
}

# Simple entity confidence thresholds (replacing deduplikacja logic)
ENTITY_CONFIDENCE_THRESHOLDS = {
    "CHARACTER": 0.4,
    "LOCATION": 0.3,
    "ADDRESS": 0.5,
    "INSTITUTION": 0.4,
    "DATE": 0.6,
    "default": 0.3
}

def get_confidence_threshold_for_type(entity_type: str) -> float:
    """Get confidence threshold for entity type (replaces merge thresholds)"""
    return ENTITY_CONFIDENCE_THRESHOLDS.get(entity_type, ENTITY_CONFIDENCE_THRESHOLDS["default"])


# Utility functions
def get_all_entity_types() -> List[str]:
    """Get all available entity types"""
    return [e.value for e in EntityType]


def get_all_relationship_types() -> List[str]:
    """Get all available relationship types"""
    return [r.value for r in RelationType]