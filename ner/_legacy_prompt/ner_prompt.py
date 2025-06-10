"""
NER Prompt wrapper class
"""

from .semantic_cleaning import get_semantic_cleaning_prompt
from .meta_analysis import get_chunk_analysis_prompt
from .entity_extraction import get_entity_extraction_prompt
from .custom_extraction import build_custom_extraction_prompt


class NERPrompt:
    """Wrapper class for prompt functions"""
    
    @classmethod
    def get_semantic_cleaning_prompt(cls, text: str) -> str:
        return get_semantic_cleaning_prompt(text)
    
    @classmethod
    def get_chunk_analysis_prompt(cls, text: str) -> str:
        return get_chunk_analysis_prompt(text)
    
    @classmethod
    def get_entity_extraction_prompt(cls, text: str) -> str:
        return get_entity_extraction_prompt(text)
    
    @classmethod
    def build_custom_extraction_prompt(cls, text: str, custom_instructions: str) -> str:
        return build_custom_extraction_prompt(text, custom_instructions)