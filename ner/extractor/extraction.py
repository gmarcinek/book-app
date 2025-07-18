"""
ner/extractor/extraction.py

Clean entity extraction - batch processing with relationship support
"""
import logging
from typing import List, Tuple
from ..semantic import TextChunk
from ..domains import BaseNER, DomainFactory
from ..domains.auto import AutoNER
from .meta_prompt import _build_chunk_analysis_prompt, _parse_custom_prompt, _build_custom_extraction_prompt, _build_extraction_prompt
from .parsing import _parse_llm_response
from .validation import _validate_and_clean_entity

logger = logging.getLogger(__name__)


def extract_entities_from_chunk_multi_domain(extractor, chunk: TextChunk, domains: List[BaseNER], domain_names: List[str], chunk_id: str = None) -> Tuple[List, List]:
    """Extract entities and relationships from chunk with auto-classification support"""
    
    # Auto-classification if needed
    if domain_names == ["auto"]:
        domains, domain_names = _auto_classify_chunk(extractor, chunk)
    
    # Multi-domain extraction
    all_entities = []
    all_relationships = []
    logger.info(f"⚙️ Processing chunk {chunk.id} with {len(domains)} domains: {domain_names}")
    
    for domain, domain_name in zip(domains, domain_names):
        try:
            entities, relationships = _extract_entities_single_domain(extractor, chunk, domain, domain_name)
            
            for entity in entities:
                entity.domain = domain_name
            
            all_entities.extend(entities)
            all_relationships.extend(relationships)
            _update_domain_stats(extractor, domain_name, entities)
            
            logger.info(f"📊 Domain '{domain_name}': {len(entities)} entities, {len(relationships)} relationships from chunk {chunk.id}")
            
        except Exception as e:
            logger.error(f"💥 Error with domain '{domain_name}' for chunk {chunk.id}: {e}")
            continue
    
    logger.info(f"✅ Chunk {chunk.id}: {len(all_entities)} total entities, {len(all_relationships)} relationships from {len(domains)} domains")
    return all_entities, all_relationships


def _auto_classify_chunk(extractor, chunk: TextChunk):
    """Auto-classify chunk to determine domains"""
    logger.info(f"🤖 Auto-classifying chunk {chunk.id}")
    
    try:
        classifier = AutoNER()
        detected_domains = classifier.classify_chunk_with_llm(chunk.text, extractor._call_llm_for_auto_classification)
        domains = DomainFactory.use(detected_domains)
        logger.info(f"🎯 Chunk {chunk.id} classified as: {detected_domains}")
        return domains, detected_domains
    except Exception as e:
        logger.error(f"💥 Auto-classification failed for chunk {chunk.id}: {e}")
        fallback_domains = DomainFactory.use(["literary"])
        logger.info(f"🔄 Using fallback domain 'literary'")
        return fallback_domains, ["literary"]


def _extract_entities_single_domain(extractor, chunk: TextChunk, domain: BaseNER, domain_name: str) -> Tuple[List, List]:
    """Extract entities and relationships for single domain"""
    try:
        # Build enhanced prompts
        extraction_prompt = _build_extraction_prompt_with_context(extractor, chunk, domain, domain_name)
        
        # Execute extraction
        response = extractor._call_llm_for_entity_extraction(extraction_prompt)
        
        # Parse entities and relationships
        raw_entities, raw_relationships = _parse_llm_response(response)
        extractor.extraction_stats["entities_extracted_raw"] += len(raw_entities)
        
        # Validate entities
        valid_entities = _validate_entities(extractor, raw_entities, domain, chunk, domain_name)
        
        logger.info(f"🎯 Domain '{domain_name}': {len(raw_entities)} raw entities → {len(valid_entities)} valid, {len(raw_relationships)} relationships")
        return valid_entities, raw_relationships
        
    except Exception as e:
        logger.error(f"💥 Extraction failed for domain '{domain_name}': {e}")
        extractor.extraction_stats["failed_extractions"] += 1
        return [], []


def _build_extraction_prompt_with_context(extractor, chunk: TextChunk, domain: BaseNER, domain_name: str) -> str:
    """Build extraction prompt with contextual enhancement"""
    
    # Get contextual entities if available
    contextual_entities = _get_contextual_entities(extractor, chunk)
    
    # Try meta-analysis first
    custom_instructions = _try_meta_analysis(extractor, chunk, domain, domain_name, contextual_entities)
    
    print(f"🔍 DEBUG CUSTOM: custom_instructions = {repr(custom_instructions)}")
    print(f"🔍 DEBUG CUSTOM: len = {len(custom_instructions) if custom_instructions else 0}")

    if custom_instructions:
        print(f"🔍 DEBUG CUSTOM: Using CUSTOM extraction prompt")
        known_aliases = _get_known_aliases(extractor, chunk)
        print(f"🔍 DEBUG CUSTOM: known_aliases = {len(known_aliases) if known_aliases else 0} items")
        return _build_custom_prompt_with_aliases(domain, chunk.text, custom_instructions, known_aliases)
    else:
        print(f"🔍 DEBUG CUSTOM: Using FALLBACK extraction prompt - meta failed")
        _update_meta_stats(extractor, domain_name, failed=True)
        return _build_extraction_prompt(chunk.text, domain)


def _get_contextual_entities(extractor, chunk: TextChunk) -> List[dict]:
   """Get contextual entities for NER enhancement"""
   if not extractor.semantic_store:
       print(f"🔍 CONTEXTUAL: No semantic store available")
       return []
   
   try:
       print(f"🔍 CONTEXTUAL: Searching for entities similar to: '{chunk.text}'")
       print(f"🔍 CONTEXTUAL: Store has {len(extractor.semantic_store.entities)} total entities")
       
       entities = extractor.semantic_store.get_contextual_entities_for_ner(chunk.text, max_entities=8)
       
       print(f"🔍 CONTEXTUAL: get_contextual_entities_for_ner returned {len(entities)} entities")
       
       # Enhanced format with semantic relations
       enhanced_entities = []
       for entity in entities:
           print(f"🔍 CONTEXTUAL: Processing entity: {entity.get('id')} {entity.get('name')} ({entity.get('type')})")
           
           enhanced = {
               'id': entity['id'],
               'name': entity['name'],
               'type': entity['type'],
               'description': entity['description'],
               'semantic_relations': [
                   f"występuje_z innymi encjami typu {entity['type']}",
                   f"ma_aliasy {', '.join(entity['aliases'][:3])}" if entity.get('aliases') else ""
               ]
           }
           # Remove empty relations
           enhanced['semantic_relations'] = [rel for rel in enhanced['semantic_relations'] if rel]
           enhanced_entities.append(enhanced)
       
       print(f"🔍 CONTEXTUAL: Final enhanced_entities count: {len(enhanced_entities)}")
       
       if enhanced_entities:
           extractor.extraction_stats["semantic_enhancements"] += 1
           logger.info(f"🧠 Found {len(enhanced_entities)} contextual entities with semantic relations")
       return enhanced_entities
   except Exception as e:
       print(f"🔍 CONTEXTUAL: EXCEPTION - {e}")
       logger.warning(f"⚠️ Contextual lookup failed: {e}")
       return []


def _try_meta_analysis(extractor, chunk: TextChunk, domain: BaseNER, domain_name: str, contextual_entities: List[dict]) -> str:
    """Try meta-analysis to get custom instructions"""
    try:
        base_prompt = _build_chunk_analysis_prompt(chunk.text, domain, contextual_entities)

        response = extractor._call_llm_for_meta_analysis(base_prompt)
        custom_instructions = _parse_custom_prompt(response, force_raw=True)
        
        if custom_instructions:
            _update_meta_stats(extractor, domain_name, failed=False)
            logger.info(f"🧠 Meta-analysis succeeded for chunk {chunk.id}")
            return custom_instructions
        else:
            _update_meta_stats(extractor, domain_name, failed=True)
            return None
            
    except Exception as e:
        logger.warning(f"🔴 Meta-analysis failed: {e}")
        _update_meta_stats(extractor, domain_name, failed=True)
        return None


def _get_known_aliases(extractor, chunk: TextChunk) -> List[dict]:  # ZMIANA: Lista zamiast dict
    """Get known aliases for chunk using contextual entities"""
    if not extractor.semantic_store:
        return []
    
    try:
        # ZAMIANA: użyj get_contextual_entities_for_ner
        contextual_entities = extractor.semantic_store.get_contextual_entities_for_ner(
            chunk.text, 
            max_entities=8,
            threshold=0.6  # lub inny sensowny threshold
        )
        
        if contextual_entities:
            logger.info(f"🏷️ Found {len(contextual_entities)} contextual entities with context")
        return contextual_entities
        
    except Exception as e:
        logger.warning(f"⚠️ Contextual entities lookup failed: {e}")
        return []


def _build_custom_prompt_with_aliases(domain: BaseNER, text: str, custom_instructions: str, known_aliases) -> str:
    print(f"🔍 DEBUG BUILD_CUSTOM: called with {len(custom_instructions)} chars instructions")
    print(f"🔍 DEBUG BUILD_CUSTOM: known_aliases = {known_aliases}")
    
    if hasattr(domain, 'build_custom_extraction_prompt'):
        print(f"🔍 DEBUG BUILD_CUSTOM: domain HAS build_custom_extraction_prompt")
        try:
            result = domain.build_custom_extraction_prompt(text, custom_instructions, known_aliases)
            print(f"🔍 DEBUG BUILD_CUSTOM: SUCCESS - using domain custom method")
            return result
        except Exception as e:
            print(f"🔍 DEBUG BUILD_CUSTOM: EXCEPTION in domain method: {e}")
    else:
        print(f"🔍 DEBUG BUILD_CUSTOM: domain MISSING build_custom_extraction_prompt")
    
    print(f"🔍 DEBUG BUILD_CUSTOM: FALLBACK to standard method")
    return _build_custom_extraction_prompt(text, custom_instructions, domain)


def _validate_entities(extractor, raw_entities: List[dict], domain: BaseNER, chunk: TextChunk, domain_name: str) -> List:
    """Validate and create ExtractedEntity objects"""
    valid_entities = []
    
    for entity_data in raw_entities:
        cleaned = _validate_and_clean_entity(entity_data, domain)
        
        if cleaned:
            context = _find_entity_context(cleaned['name'], chunk.text)
            _update_context_stats(extractor, cleaned['name'], context)
            
            from .base import ExtractedEntity
            entity = ExtractedEntity(
                name=cleaned['name'],
                type=cleaned['type'],
                description=cleaned['description'],
                confidence=cleaned['confidence'],
                aliases=cleaned['aliases'],
                chunk_id=chunk.id,
                context=context,
                domain=domain_name,
                evidence=cleaned.get('evidence', '')
            )
            
            valid_entities.append(entity)
            extractor.extraction_stats["entities_extracted_valid"] += 1
        else:
            extractor.extraction_stats["entities_rejected"] += 1
    
    return valid_entities


def _find_entity_context(entity_name: str, chunk_text: str, window: int = 100) -> str:
    """Find context around entity"""
    pos = chunk_text.lower().find(entity_name.lower())
    if pos == -1:
        return ""
    
    start = max(0, pos - window)
    end = min(len(chunk_text), pos + len(entity_name) + window)
    return chunk_text[start:end].strip()


def _update_context_stats(extractor, entity_name: str, context: str):
    """Update context statistics"""
    extractor.context_stats['contexts_generated'] += 1
    
    if entity_name.lower() in context.lower():
        extractor.context_stats['entities_found_in_context'] += 1
    else:
        extractor.context_stats['fallback_contexts_used'] += 1


def _update_domain_stats(extractor, domain_name: str, entities: List):
    """Update per-domain statistics"""
    raw_count = len(entities)
    valid_count = sum(1 for e in entities if e.confidence >= 0.3)
    
    extractor.extraction_stats["by_domain"][domain_name]["raw"] += raw_count
    extractor.extraction_stats["by_domain"][domain_name]["valid"] += valid_count


def _update_meta_stats(extractor, domain_name: str, failed: bool):
    """Update meta-prompt statistics"""
    extractor.meta_prompt_stats['meta_prompts_generated'] += 1
    extractor.meta_prompt_stats['by_domain'][domain_name]['generated'] += 1
    
    if failed:
        extractor.meta_prompt_stats['meta_prompts_failed'] += 1
        extractor.meta_prompt_stats['fallback_to_standard_prompt'] += 1
        extractor.meta_prompt_stats['by_domain'][domain_name]['failed'] += 1