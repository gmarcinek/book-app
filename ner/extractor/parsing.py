"""
Parsowanie JSON: _parse_llm_response()
"""

import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def _parse_llm_response(response: str) -> List[Dict[str, Any]]:
    """Parse LLM JSON response into entities list"""
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
                # Remove language identifier if present
                if clean_response.startswith('json'):
                    clean_response = clean_response[4:]
        
        # Parse JSON
        data = json.loads(clean_response.strip())
        
        # Extract entities list
        if isinstance(data, dict) and 'entities' in data:
            entities = data['entities']
        elif isinstance(data, list):
            entities = data
        else:
            logger.warning(f"Unexpected response format: {type(data)}")
            return []
        
        # Ensure entities is a list
        if not isinstance(entities, list):
            logger.warning(f"Entities is not a list: {type(entities)}")
            return []
        
        return entities
            
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        logger.error(f"Raw response (first 300 chars): {response[:300]}")
        return []
    except Exception as e:
        logger.error(f"Error parsing LLM response: {e}")
        return []