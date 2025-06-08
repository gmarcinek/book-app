"""
Walidacja danych: _validate_and_clean_entity()
"""

import logging
from typing import Dict, Any, Optional
from ..utils import validate_entity_name, validate_entity_type
from ..consts import ENTITY_TYPES_FLAT as ENTITY_TYPES

logger = logging.getLogger(__name__)


def _validate_and_clean_entity(entity_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate and clean entity data + aliases
    
    Returns:
        Cleaned entity dict or None if invalid
    """
    # Check required fields
    if not isinstance(entity_data, dict):
        return None
    
    name = entity_data.get('name', '').strip()
    entity_type = entity_data.get('type', '').strip().upper()
    
    if not name or not entity_type:
        logger.info(f"Missing name or type: {entity_data}")
        return None
    
    # Validate name
    if not validate_entity_name(name):
        logger.info(f"Invalid entity name: '{name}'")
        return None
    
    # Validate type
    if entity_type not in ENTITY_TYPES:
        logger.info(f"Invalid entity type: '{entity_type}' (valid types: {ENTITY_TYPES})")
        return None
    
    # Clean and validate description
    description = str(entity_data.get('description', '')).strip()
    
    # Validate and normalize confidence
    confidence = entity_data.get('confidence', 0.5)
    try:
        confidence = float(confidence)
        confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1 range
    except (ValueError, TypeError):
        confidence = 0.5
    
    # Reject entities with very low confidence
    if confidence < 0.3:
        logger.info(f"Rejected low confidence entity: {name} ({confidence})")
        return None
    
    # ← NOWE: Validate and clean aliases
    aliases = entity_data.get('aliases', [])
    if not isinstance(aliases, list):
        aliases = []
    
    # Clean aliases - remove empty, duplicates, and the main name
    cleaned_aliases = []
    for alias in aliases:
        if isinstance(alias, str):
            alias_clean = alias.strip()
            if (alias_clean and 
                alias_clean.lower() != name.lower() and 
                alias_clean not in cleaned_aliases):
                cleaned_aliases.append(alias_clean)
    
    return {
        'name': name,
        'type': entity_type,
        'description': description,
        'confidence': confidence,
        'aliases': cleaned_aliases  # ← NOWE
    }