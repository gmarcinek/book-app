"""
NER Entity Extractor - Tylko ekstrakcja encji + META-PROMPT SYSTEM + ALIASES
"""

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

# Local imports
from .utils import load_ner_config, log_memory_usage, validate_entity_name, validate_entity_type
from .chunker import TextChunk
from .prompt import NERPrompt
from .consts import ENTITY_TYPES_FLAT as ENTITY_TYPES
from llm import Models

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    """Represents an extracted entity"""
    name: str
    type: str
    description: str
    confidence: float
    aliases: List[str] = None
    chunk_id: Optional[int] = None
    context: Optional[str] = None
    
    def __post_init__(self):
        """Initialize aliases as empty list if None"""
        if self.aliases is None:
            self.aliases = []


class EntityExtractor:
    """
    Uproszczony ekstraktor encji - bez relacji + META-PROMPT SYSTEM
    """
    
    def __init__(self, model: str = Models.QWEN_CODER, config_path: str = "ner/ner_config.json"):
        self.config = load_ner_config(config_path)
        self.model = model
        self.llm_client = None
        self.extraction_stats = {
            "chunks_processed": 0,
            "entities_extracted_raw": 0,
            "entities_extracted_valid": 0,
            "entities_rejected": 0,
            "failed_extractions": 0
        }
        self.context_stats = {
            'contexts_generated': 0,
            'entities_found_in_context': 0,
            'fallback_contexts_used': 0
        }
        # ← NOWE: stats dla meta-prompt systemu
        self.meta_prompt_stats = {
            'meta_prompts_generated': 0,
            'meta_prompts_failed': 0,
            'fallback_to_standard_prompt': 0
        }
    
    def _initialize_llm(self):
        """Initialize LLM client if needed"""
        if self.llm_client is None:
            try:
                from llm import LLMClient
                self.llm_client = LLMClient(self.model)
                logger.info(f"Initialized LLM model: {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize LLM: {e}")
                raise
    
    def _build_extraction_prompt(self, text: str) -> str:
        """Build entity extraction prompt using centralized prompts (FALLBACK)"""
        return NERPrompt.get_entity_extraction_prompt(text)
    
    # ← NOWE: Meta-prompt system methods
    def _build_chunk_analysis_prompt(self, text: str) -> str:
        """Build meta-prompt for chunk analysis"""
        return NERPrompt.get_chunk_analysis_prompt(text)
    
    def _parse_custom_prompt(self, response: str) -> Optional[str]:
        """Parse custom NER prompt from meta-prompt response"""
        try:
            # Extract content between <CUSTOM_NER_PROMPT> tags
            if '<CUSTOM_NER_PROMPT>' in response and '</CUSTOM_NER_PROMPT>' in response:
                start = response.find('<CUSTOM_NER_PROMPT>') + len('<CUSTOM_NER_PROMPT>')
                end = response.find('</CUSTOM_NER_PROMPT>')
                custom_prompt = response[start:end].strip()
                
                if len(custom_prompt) > 50:  # Basic validation
                    return custom_prompt
            
            logger.warning("Failed to parse custom prompt from meta-prompt response")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing custom prompt: {e}")
            return None
    
    def _build_custom_extraction_prompt(self, text: str, custom_instructions: str) -> str:
        """Build final extraction prompt using custom instructions"""
        return NERPrompt.build_custom_extraction_prompt(text, custom_instructions)
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt and return response"""
        try:
            if self.llm_client is None:
                self._initialize_llm()
            
            response = self.llm_client.chat(prompt)
            return response
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
    
    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
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
    
    def _validate_and_clean_entity(self, entity_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
    
    def _find_entity_context(self, entity_name: str, chunk_text: str, context_window: int = 100) -> str:
        return ""
    
    def _validate_entity_context(self, entity_name: str, context: str) -> bool:
        """
        Validate that entity actually appears in its context
        
        Returns:
            True if entity found in context, False otherwise
        """
        return entity_name.lower() in context.lower()
    
    def _update_context_stats(self, entity_name: str, context: str):
        """Update statistics about context quality"""
        self.context_stats['contexts_generated'] += 1
        
        if self._validate_entity_context(entity_name, context):
            self.context_stats['entities_found_in_context'] += 1
    
    def _extract_entities_from_chunk(self, chunk: TextChunk) -> List[ExtractedEntity]:
        """
        Extract and validate entities from a single text chunk
        ← NOWE: Uses 2-step meta-prompt process
        """
        try:
            # ← KROK 1: ROZGRZEWKA - analiza chunka i generowanie custom promptu
            meta_prompt = self._build_chunk_analysis_prompt(chunk.text)
            meta_response = self._call_llm(meta_prompt)
            self.meta_prompt_stats['meta_prompts_generated'] += 1
            
            # Parse custom prompt from meta-response
            custom_instructions = self._parse_custom_prompt(meta_response)
            
            if custom_instructions:
                # ← KROK 2A: EXTRACTION z custom promptem
                prompt = self._build_custom_extraction_prompt(chunk.text, custom_instructions)
                logger.info(f"Using custom prompt for chunk {chunk.id}")
            else:
                # ← KROK 2B: FALLBACK do standardowego promptu
                prompt = self._build_extraction_prompt(chunk.text)
                self.meta_prompt_stats['meta_prompts_failed'] += 1
                self.meta_prompt_stats['fallback_to_standard_prompt'] += 1
                logger.warning(f"Meta-prompt failed for chunk {chunk.id}, using fallback")
            
            # Call LLM for actual extraction
            response = self._call_llm(prompt)
            
            # Parse response
            raw_entities = self._parse_llm_response(response)
            self.extraction_stats["entities_extracted_raw"] += len(raw_entities)
            
            # Validate and convert to ExtractedEntity objects
            valid_entities = []
            for entity_data in raw_entities:
                cleaned_entity = self._validate_and_clean_entity(entity_data)
                
                if cleaned_entity:
                    # Find entity context
                    entity_context = self._find_entity_context(cleaned_entity['name'], chunk.text)
                    
                    # Update context statistics
                    self._update_context_stats(cleaned_entity['name'], entity_context)
                    
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
                    self.extraction_stats["entities_extracted_valid"] += 1
                else:
                    self.extraction_stats["entities_rejected"] += 1
            
            logger.info(f"Chunk {chunk.id}: {len(raw_entities)} raw → {len(valid_entities)} valid entities")
            return valid_entities
            
        except Exception as e:
            logger.error(f"Failed to extract entities from chunk {chunk.id}: {e}")
            self.extraction_stats["failed_extractions"] += 1
            return []
    
    def _deduplicate_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """
        Remove duplicate entities based on normalized names + aliases
        Keep the entity with highest confidence
        ← NOWE: Uwzględnia aliases w deduplikacji
        """
        if not entities:
            return entities
        
        # Group entities by normalized name and aliases
        entity_groups = {}
        
        for entity in entities:
            # Create set of all possible names (main + aliases)
            all_names = {entity.name.lower().strip()}
            for alias in entity.aliases:
                all_names.add(alias.lower().strip())
            
            # Find if entity belongs to existing group
            found_group = None
            for group_key, group_names in entity_groups.items():
                if any(name in group_names for name in all_names):
                    found_group = group_key
                    break
            
            if found_group:
                # Add to existing group
                entity_groups[found_group]['entities'].append(entity)
                entity_groups[found_group]['all_names'].update(all_names)
            else:
                # Create new group
                normalized_key = entity.name.lower().strip()
                entity_groups[normalized_key] = {
                    'entities': [entity],
                    'all_names': all_names
                }
        
        # Keep best entity from each group
        deduplicated = []
        duplicates_removed = 0
        
        for group_key, group_data in entity_groups.items():
            entities_in_group = group_data['entities']
            
            if len(entities_in_group) == 1:
                deduplicated.append(entities_in_group[0])
            else:
                # Keep entity with highest confidence
                best_entity = max(entities_in_group, key=lambda e: e.confidence)
                
                # Merge aliases from all entities in group
                all_aliases = set()
                for entity in entities_in_group:
                    all_aliases.update(entity.aliases)
                    # Add main names of other entities as aliases
                    if entity != best_entity:
                        all_aliases.add(entity.name)
                
                # Remove main name from aliases
                all_aliases.discard(best_entity.name.lower())
                all_aliases.discard(best_entity.name)
                
                best_entity.aliases = list(all_aliases)
                deduplicated.append(best_entity)
                duplicates_removed += len(entities_in_group) - 1
                
                logger.info(f"Deduplicated '{group_key}': kept 1 of {len(entities_in_group)} entities, merged aliases")
        
        if duplicates_removed > 0:
            logger.info(f"Removed {duplicates_removed} duplicate entities, merged aliases")
        
        return deduplicated
    
    def extract_entities(self, chunks: List[TextChunk]) -> List[ExtractedEntity]:
        """Extract entities from multiple text chunks with deduplication"""
        self._initialize_llm()
        
        all_entities = []
        
        logger.info(f"Starting entity extraction from {len(chunks)} chunks")
        
        for chunk in chunks:
            try:
                entities = self._extract_entities_from_chunk(chunk)
                all_entities.extend(entities)
                
                self.extraction_stats["chunks_processed"] += 1
                
                # Log progress every 5 chunks
                if self.extraction_stats["chunks_processed"] % 5 == 0:
                    logger.info(f"Processed {self.extraction_stats['chunks_processed']}/{len(chunks)} chunks")
                
                # Memory management
                log_memory_usage(f"After chunk {chunk.id}")
                
            except Exception as e:
                logger.error(f"Error processing chunk {chunk.id}: {e}")
                continue
        
        # Deduplicate entities
        logger.info(f"Deduplicating {len(all_entities)} entities...")
        deduplicated_entities = self._deduplicate_entities(all_entities)
        
        # Final stats
        validation_rate = (self.extraction_stats["entities_extracted_valid"] / 
                          self.extraction_stats["entities_extracted_raw"] 
                          if self.extraction_stats["entities_extracted_raw"] > 0 else 0)
        
        context_accuracy = (self.context_stats["entities_found_in_context"] / 
                           self.context_stats["contexts_generated"] 
                           if self.context_stats["contexts_generated"] > 0 else 0)
        
        # ← NOWE: Meta-prompt stats
        meta_success_rate = ((self.meta_prompt_stats['meta_prompts_generated'] - 
                             self.meta_prompt_stats['meta_prompts_failed']) / 
                            self.meta_prompt_stats['meta_prompts_generated'] 
                            if self.meta_prompt_stats['meta_prompts_generated'] > 0 else 0)
        
        logger.info(f"Entity extraction complete:")
        logger.info(f"  Chunks processed: {self.extraction_stats['chunks_processed']}")
        logger.info(f"  Raw entities: {self.extraction_stats['entities_extracted_raw']}")
        logger.info(f"  Valid entities: {self.extraction_stats['entities_extracted_valid']}")
        logger.info(f"  Final entities (after dedup): {len(deduplicated_entities)}")
        logger.info(f"  Validation rate: {validation_rate:.1%}")
        logger.info(f"  Context accuracy: {context_accuracy:.1%}")
        logger.info(f"  Meta-prompt success rate: {meta_success_rate:.1%}")
        logger.info(f"  Fallback to standard prompt: {self.meta_prompt_stats['fallback_to_standard_prompt']}")
        
        return deduplicated_entities
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get detailed extraction statistics"""
        stats = self.extraction_stats.copy()
        stats.update(self.context_stats)
        stats.update(self.meta_prompt_stats)  # ← NOWE
        
        if stats["entities_extracted_raw"] > 0:
            stats["validation_rate"] = stats["entities_extracted_valid"] / stats["entities_extracted_raw"]
            stats["rejection_rate"] = stats["entities_rejected"] / stats["entities_extracted_raw"]
        else:
            stats["validation_rate"] = 0
            stats["rejection_rate"] = 0
        
        if stats["contexts_generated"] > 0:
            stats["context_accuracy"] = stats["entities_found_in_context"] / stats["contexts_generated"]
            stats["fallback_rate"] = stats["fallback_contexts_used"] / stats["contexts_generated"]
        else:
            stats["context_accuracy"] = 0
            stats["fallback_rate"] = 0
        
        # ← NOWE: Meta-prompt stats
        if stats["meta_prompts_generated"] > 0:
            stats["meta_prompt_success_rate"] = ((stats["meta_prompts_generated"] - stats["meta_prompts_failed"]) / 
                                                stats["meta_prompts_generated"])
        else:
            stats["meta_prompt_success_rate"] = 0
        
        return stats