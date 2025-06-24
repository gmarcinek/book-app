"""
Meta-prompt system: _build_chunk_analysis_prompt(), _parse_custom_prompt()
Uses utils for robust JSON parsing
"""

import logging
from typing import Optional, List
from ..domains import BaseNER
from ..utils import parse_llm_json_response

logger = logging.getLogger(__name__)


def _build_chunk_analysis_prompt(text: str, domain: BaseNER, contextual_entities: List[dict] = None) -> str:
    """Build meta-prompt for chunk analysis using domain-specific prompt"""
    return domain.get_meta_analysis_prompt(text, contextual_entities)


def _parse_custom_prompt(response: str, force_raw: bool = False) -> Optional[str]:
    """
    Parse custom prompt from LLM meta-prompt response.
    If force_raw=True, just return the whole response stripped.
    """
    if force_raw:
        return response.strip()

    data = parse_llm_json_response(response, expected_key="prompt")
    return data.get("prompt") if data else None


def _build_custom_extraction_prompt(text: str, custom_instructions: str, domain: BaseNER) -> str:
    """Build final extraction prompt using custom instructions and domain-specific template"""
    return domain.build_custom_extraction_prompt(text, custom_instructions)


def _build_extraction_prompt(text: str, domain: BaseNER) -> str:
    """Build fallback extraction prompt using domain-specific base prompt"""
    return domain.get_base_extraction_prompt(text)