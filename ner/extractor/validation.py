"""
Walidacja danych: _validate_and_clean_entity() - Domain-aware version with proper config usage
"""

import logging
from typing import Dict, Any, Optional
from ..utils import validate_entity_name, validate_entity_type
from ..domains import BaseNER

logger = logging.getLogger(__name__)


def _validate_and_clean_entity(entity_data: Dict[str, Any], domain: BaseNER = None) -> Optional[Dict[str, Any]]:
    """
    Validate and clean entity data + aliases using domain-specific rules and proper config thresholds
    
    Args:
        entity_data: Raw entity data from LLM
        domain: Domain instance for domain-specific validation
    
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
    
    # Domain-specific entity type validation
    if domain:
        valid_types = domain.get_entity_types()
        if entity_type not in valid_types:
            logger.info(f"Invalid entity type '{entity_type}' for domain '{domain.config.name}' (valid: {valid_types[:5]}...)")
            return None
        
        # Additional domain-specific validation
        if hasattr(domain, 'validate_entity') and not domain.validate_entity(entity_data):
            logger.info(f"Entity '{name}' rejected by domain '{domain.config.name}' validation")
            return None
    else:
        # Fallback: use basic type validation
        if not validate_entity_type(entity_type):
            logger.info(f"Invalid entity type: '{entity_type}'")
            return None
    
    # Clean and validate description
    description = str(entity_data.get('description', '')).strip()
    
    # Validate and normalize confidence - use sensible defaults
    confidence = entity_data.get('confidence', 0.5)  # Default 0.5 instead of BASE_SIMILARITY_THRESHOLD
    try:
        confidence = float(confidence)
        confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1 range
    except (ValueError, TypeError):
        confidence = 0.5  # Fallback to sensible default
    
    # Use proper confidence threshold - domain-specific if available, otherwise sensible minimum
    if domain and hasattr(domain, 'get_confidence_threshold'):
        min_confidence = domain.get_confidence_threshold(entity_type)
    else:
        # Use a sensible minimum for entity validation (not search threshold)
        # Different thresholds for different entity types based on precision needs
        from ner.types import get_confidence_threshold_for_type
        try:
            # Get type-specific confidence threshold
            min_confidence = get_confidence_threshold_for_type(entity_type)
            # Make validation slightly more lenient than extraction threshold
            min_confidence = max(0.15, min_confidence - 0.1)
        except:
            min_confidence = 0.2  # Safe fallback for validation
    
    # Reject entities with confidence below threshold
    if confidence < min_confidence:
        logger.info(f"Rejected low confidence entity: {name} ({confidence:.2f} < {min_confidence:.2f}) for domain {domain.config.name if domain else 'default'}")
        return None
    
    # Validate and clean aliases
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
        'aliases': cleaned_aliases,
        'evidence': entity_data.get('evidence', '')
    }