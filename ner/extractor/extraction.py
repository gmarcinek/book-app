"""
Właściwa ekstrakcja encji: _extract_entities_from_chunk() (bez meta-prompt części)
"""

import logging
from typing import List
from ..chunker import TextChunk
from ..prompt import NERPrompt
from .meta_prompt import _build_chunk_analysis_prompt, _parse_custom_prompt, _build_custom_extraction_prompt
from .parsing import _parse_llm_response
from .validation import _validate_and_clean_entity

logger = logging.getLogger(__name__)


def _build_extraction_prompt(text: str) -> str:
    """Build entity extraction prompt using centralized prompts (FALLBACK)"""
    return NERPrompt.get_entity_extraction_prompt(text)


def _find_entity_context(entity_name: str, chunk_text: str, context_window: int = 100) -> str:
    return ""


def _validate_entity_context(entity_name: str, context: str) -> bool:
    """
    Validate that entity actually appears in its context
    
    Returns:
        True if entity found in context, False otherwise
    """
    return entity_name.lower() in context.lower()


def _update_context_stats(extractor, entity_name: str, context: str):
    """Update statistics about context quality"""
    extractor.context_stats['contexts_generated'] += 1
    
    if _validate_entity_context(entity_name, context):
        extractor.context_stats['entities_found_in_context'] += 1


def _extract_entities_from_chunk(extractor, chunk: TextChunk) -> List:
    """
    Extract and validate entities from a single text chunk
    ← NOWE: Uses 2-step meta-prompt process
    """
    try:
        # ← KROK 1: ROZGRZEWKA - analiza chunka i generowanie custom promptu
        meta_prompt = _build_chunk_analysis_prompt(chunk.text)
        meta_response = extractor._call_llm(meta_prompt, extractor.extractor_config.get_meta_analysis_temperature())
        extractor.meta_prompt_stats['meta_prompts_generated'] += 1
        
        # Parse custom prompt from meta-response
        custom_instructions = _parse_custom_prompt(meta_response)
        
        if custom_instructions:
            # ← KROK 2A: EXTRACTION z custom promptem
            prompt = _build_custom_extraction_prompt(chunk.text, custom_instructions)
            logger.info(f"Using custom prompt for chunk {chunk.id}")
        else:
            # ← KROK 2B: FALLBACK do standardowego promptu
            prompt = _build_extraction_prompt(chunk.text)
            extractor.meta_prompt_stats['meta_prompts_failed'] += 1
            extractor.meta_prompt_stats['fallback_to_standard_prompt'] += 1
            logger.warning(f"Meta-prompt failed for chunk {chunk.id}, using fallback")
        
        # Call LLM for actual extraction
        response = extractor._call_llm(prompt, extractor.extractor_config.get_entity_extraction_temperature())
        
        # Parse response
        raw_entities = _parse_llm_response(response)
        extractor.extraction_stats["entities_extracted_raw"] += len(raw_entities)
        
        # Validate and convert to ExtractedEntity objects
        valid_entities = []
        for entity_data in raw_entities:
            cleaned_entity = _validate_and_clean_entity(entity_data)
            
            if cleaned_entity:
                # Find entity context
                entity_context = _find_entity_context(cleaned_entity['name'], chunk.text)
                
                # Update context statistics
                _update_context_stats(extractor, cleaned_entity['name'], entity_context)
                
                from .base import ExtractedEntity
                entity = ExtractedEntity(
                    name=cleaned_entity['name'],
                    type=cleaned_entity['type'],
                    description=cleaned_entity['description'],
                    confidence=cleaned_entity['confidence'],
                    aliases=cleaned_entity['aliases'],  # ← NOWE
                    chunk_id=chunk.id,
                    context=entity_context
                )
                valid_entities.append(entity)
                extractor.extraction_stats["entities_extracted_valid"] += 1
            else:
                extractor.extraction_stats["entities_rejected"] += 1
        
        logger.info(f"Chunk {chunk.id}: {len(raw_entities)} raw → {len(valid_entities)} valid entities")
        return valid_entities
        
    except Exception as e:
        logger.error(f"Failed to extract entities from chunk {chunk.id}: {e}")
        extractor.extraction_stats["failed_extractions"] += 1
        return []