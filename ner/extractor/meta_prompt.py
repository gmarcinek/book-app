"""
Meta-prompt system: _build_chunk_analysis_prompt(), _parse_custom_prompt()
"""

import json
import logging
from typing import Optional
from ..prompt import NERPrompt

logger = logging.getLogger(__name__)


def _build_chunk_analysis_prompt(text: str) -> str:
    """Build meta-prompt for chunk analysis"""
    return NERPrompt.get_chunk_analysis_prompt(text)


def _parse_custom_prompt(response: str) -> Optional[str]:
    """Parse custom NER prompt from meta-prompt response"""
    try:
        # Parse JSON response
        if '{' in response and '"prompt"' in response:
            data = json.loads(response.strip().replace('```json', '').replace('```', ''))
            return data.get('prompt')
        
        logger.warning("Failed to parse custom prompt from meta-prompt response")
        return None
        
    except Exception as e:
        logger.error(f"Error parsing custom prompt: {e}")
        return None


def _build_custom_extraction_prompt(text: str, custom_instructions: str) -> str:
    """Build final extraction prompt using custom instructions"""
    return NERPrompt.build_custom_extraction_prompt(text, custom_instructions)