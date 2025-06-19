"""
Parsowanie JSON: _parse_llm_response() + relationships
"""

import json
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


def _parse_llm_response(response: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Parse LLM JSON response into entities and relationships lists"""
    try:
        # Clean response - remove markdown formatting if present
        clean_response = response.strip()
        
        # Handle code blocks
        if '```json' in clean_response:
            clean_response = clean_response.split('```json')[1].split('```')[0]
        elif '```' in clean_response:
            parts = clean_response.split('```')
            if len(parts) >= 3:
                clean_response = parts[1]
                if clean_response.startswith('json'):
                    clean_response = clean_response[4:]
        
        # Parse JSON
        data = json.loads(clean_response.strip())
        
        # Extract entities
        if isinstance(data, dict) and 'entities' in data:
            entities = data['entities']
        elif isinstance(data, list):
            entities = data
        else:
            return [], []
        
        if not isinstance(entities, list):
            return [], []
        
        # Extract relationships
        relationships = []
        if isinstance(data, dict) and 'relationships' in data:
            relationships_raw = data['relationships']
            if isinstance(relationships_raw, list):
                relationships = relationships_raw
        
        return entities, relationships
            
    except json.JSONDecodeError as e:
        logger.error(f"❌ Failed to parse JSON response: {e}")
        return [], []
    except Exception as e:
        logger.error(f"❌ Error parsing LLM response: {e}")
        return [], []