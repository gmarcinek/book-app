"""
Entity extraction from chunks - Updated with dedicated LLM methods and auto-classification support
"""
from pathlib import Path
from datetime import datetime
import logging
from typing import List
from ..semantic import TextChunk
from ..domains import BaseNER, DomainFactory
from ..domains.auto import AutoNER
from .meta_prompt import _build_chunk_analysis_prompt, _parse_custom_prompt, _build_custom_extraction_prompt, _build_extraction_prompt
from .parsing import _parse_llm_response
from .validation import _validate_and_clean_entity

logger = logging.getLogger(__name__)


def extract_entities_from_chunk_multi_domain(extractor, chunk: TextChunk, domains: List[BaseNER], domain_names: List[str]) -> List:
    """
    Extract entities from chunk using multiple domains or auto-classification
    """
    
    # AUTO-CLASSIFICATION LOGIC
    if domain_names == ["auto"]:
        logger.info(f"🤖 Auto-classifying chunk {chunk.id}")
        
        try:
            # Use AutoNER classifier to determine domains for this chunk
            classifier = AutoNER()
            detected_domains = classifier.classify_chunk_with_llm(chunk.text, extractor._call_llm_for_auto_classification)
            
            # Get actual domain instances
            domains = DomainFactory.use(detected_domains)
            domain_names = detected_domains
            
            logger.info(f"🎯 Chunk {chunk.id} auto-classified to domains: {domain_names}")
            
        except Exception as e:
            logger.error(f"💥 Auto-classification failed for chunk {chunk.id}: {e}")
            # Fallback to literary domain
            domains = DomainFactory.use(["literary"])
            domain_names = ["literary"]
            logger.info(f"🔄 Using fallback domain 'literary' for chunk {chunk.id}")
    
    # EXISTING MULTI-DOMAIN EXTRACTION LOGIC
    all_entities = []
    
    logger.info(f"⚙️ Processing chunk {chunk.id} with {len(domains)} domains: {domain_names}")
    
    for domain, domain_name in zip(domains, domain_names):
        try:
            logger.info(f"🏷️ Extracting with domain '{domain_name}' for chunk {chunk.id}")
            
            # Extract entities using PRESERVED OLD FLOW
            entities_from_domain = _extract_entities_from_chunk_single_domain_old_flow(
                extractor, chunk, domain, domain_name
            )
            
            # Add domain info to entities
            for entity in entities_from_domain:
                entity.domain = domain_name
            
            all_entities.extend(entities_from_domain)
            
            # Update per-domain stats
            raw_count = len(entities_from_domain)
            valid_count = sum(1 for e in entities_from_domain if e.confidence >= 0.3)
            
            extractor.extraction_stats["by_domain"][domain_name]["raw"] += raw_count
            extractor.extraction_stats["by_domain"][domain_name]["valid"] += valid_count
            
            logger.info(f"📊 Domain '{domain_name}' extracted {raw_count} entities from chunk {chunk.id}")
            
        except Exception as e:
            logger.error(f"💥 Error extracting with domain '{domain_name}' for chunk {chunk.id}: {e}")
            continue
    
    logger.info(f"✅ Chunk {chunk.id}: Total {len(all_entities)} entities from {len(domains)} domains")
    return all_entities


def _extract_entities_from_chunk_single_domain_old_flow(extractor, chunk: TextChunk, domain: BaseNER, domain_name: str) -> List:
    """
    Extract entities from chunk using single domain - PRESERVED OLD FLOW with dedicated LLM methods
    This is the same logic as old _extract_entities_from_chunk() but domain-aware
    """
    try:
        # ← KROK 1: ROZGRZEWKA - analiza chunka i generowanie custom promptu (OLD FLOW)
        meta_prompt = _build_chunk_analysis_prompt(chunk.text, domain)
        _log_prompt(extractor, meta_prompt, chunk.id, f"meta_prompt_{domain_name}")
        
        # Use dedicated meta-analysis LLM method
        meta_response = extractor._call_llm_for_meta_analysis(meta_prompt)
        _log_response(extractor, meta_response, chunk.id, f"meta_prompt_{domain_name}")
        
        extractor.meta_prompt_stats['meta_prompts_generated'] += 1
        extractor.meta_prompt_stats['by_domain'][domain_name]['generated'] += 1
        
        # Parse custom prompt from meta-response (always raw mode now)
        custom_instructions = _parse_custom_prompt(meta_response, force_raw=True)
        
        if custom_instructions:
            # ← KROK 2A: EXTRACTION z custom promptem (OLD FLOW)
            prompt = _build_custom_extraction_prompt(chunk.text, custom_instructions, domain)
            logger.info(f"🧠 Using custom prompt for chunk {chunk.id}, domain '{domain_name}'")
        else:
            # ← KROK 2B: FALLBACK do standardowego promptu (OLD FLOW)
            prompt = _build_extraction_prompt(chunk.text, domain)
            _log_prompt(extractor, prompt, chunk.id, f"extraction_prompt_{domain_name}")
            
            extractor.meta_prompt_stats['meta_prompts_failed'] += 1
            extractor.meta_prompt_stats['fallback_to_standard_prompt'] += 1
            extractor.meta_prompt_stats['by_domain'][domain_name]['failed'] += 1
            
            logger.warning(f"🔴 Meta-prompt failed for chunk {chunk.id}, domain '{domain_name}', using fallback")
        
        # Use dedicated entity extraction LLM method
        response = extractor._call_llm_for_entity_extraction(prompt)
        _log_response(extractor, response, chunk.id, f"extraction_prompt_{domain_name}")
        
        # Parse response (OLD FLOW)
        raw_entities = _parse_llm_response(response)
        extractor.extraction_stats["entities_extracted_raw"] += len(raw_entities)
        
        # Validate and convert to ExtractedEntity objects (OLD FLOW + DOMAIN VALIDATION)
        valid_entities = []
        for entity_data in raw_entities:
            cleaned_entity = _validate_and_clean_entity(entity_data, domain)  # ← DOMAIN-AWARE VALIDATION
            
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
                    aliases=cleaned_entity['aliases'],
                    chunk_id=chunk.id,
                    context=entity_context,
                    domain=domain_name ,
                    evidence=cleaned_entity.get('evidence', '')
                )
                valid_entities.append(entity)
                extractor.extraction_stats["entities_extracted_valid"] += 1
            else:
                extractor.extraction_stats["entities_rejected"] += 1
        
        logger.info(f"🎯 Domain '{domain_name}', Chunk {chunk.id}: {len(raw_entities)} raw → {len(valid_entities)} valid entities")
        return valid_entities
        
    except Exception as e:
        logger.error(f"💥 Failed to extract entities from chunk {chunk.id} with domain '{domain_name}': {e}")
        extractor.extraction_stats["failed_extractions"] += 1
        return []


def _find_entity_context(entity_name: str, chunk_text: str, context_window: int = 100) -> str:
    """Find context around entity in chunk text"""
    entity_lower = entity_name.lower()
    text_lower = chunk_text.lower()
    
    pos = text_lower.find(entity_lower)
    if pos == -1:
        return ""  # Entity not found in text
    
    # Extract context window around entity
    start = max(0, pos - context_window)
    end = min(len(chunk_text), pos + len(entity_name) + context_window)
    
    context = chunk_text[start:end].strip()
    return context


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
    else:
        extractor.context_stats['fallback_contexts_used'] += 1


def _log_prompt(extractor, prompt_text: str, chunk_id: int, purpose: str):
    """Save the prompt to the aggregator log folder"""
    if hasattr(extractor, "aggregator") and hasattr(extractor.aggregator, "log_dir"):
        timestamp = datetime.now().strftime("%H%M%S")
        file_name = f"{purpose}_chunk{chunk_id}_{timestamp}.txt"
        path = extractor.aggregator.log_dir / file_name
        path.write_text(prompt_text, encoding="utf-8")


def _log_response(extractor, response_text: str, chunk_id: int, purpose: str):
    """Save the LLM response to the aggregator log folder"""
    if hasattr(extractor, "aggregator") and hasattr(extractor.aggregator, "log_dir"):
        timestamp = datetime.now().strftime("%H%M%S")
        file_name = f"{purpose}_response_chunk{chunk_id}_{timestamp}.txt"
        path = extractor.aggregator.log_dir / file_name
        path.write_text(response_text, encoding="utf-8")