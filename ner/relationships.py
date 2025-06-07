"""
NER Relationship Extractor - Poprawa jakości relacji z walidacją
"""

import json
import logging
from typing import Dict, List, Any
from dotenv import load_dotenv
load_dotenv()

# Local imports
from .utils import load_ner_config, log_memory_usage
from .prompts import NERPrompts
from .validation import RelationshipValidator
from llm import Models

logger = logging.getLogger(__name__)


class RelationshipExtractor:
    """
    Ekstraktor relacji z walidacją i filtrowaniem nonsensownych powiązań
    """
    
    def __init__(self, model: str = Models.QWEN_CODER, config_path: str = "ner/ner_config.json"):
        self.config = load_ner_config(config_path)
        self.model = model
        self.llm_client = None
        self.validator = RelationshipValidator()
        self.stats = {
            "processed": 0, 
            "found_raw": 0, 
            "found_valid": 0,
            "rejected": 0,
            "failed": 0
        }
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM with better error handling"""
        try:
            from llm import LLMClient
            
            if self.llm_client is None:
                self.llm_client = LLMClient(self.model)
            
            response = self.llm_client.chat(prompt)
            return response
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
    
    def _parse_response(self, response: str) -> Dict[str, List]:
        """Parse LLM response with better error handling"""
        try:
            # Clean markdown formatting
            clean = response.strip()
            if clean.startswith('```'):
                parts = clean.split('```')
                if len(parts) >= 3:
                    clean = parts[1]
                    if clean.startswith('json'):
                        clean = clean[4:]
            
            # Parse JSON
            data = json.loads(clean)
            
            # Normalize response format
            return {
                'internal': data.get('internal_relationships', []),
                'external': data.get('external_relationships', []), 
                'missing': data.get('missing_entities', [])
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            logger.warning(f"Raw response: {response[:200]}...")
            return {'internal': [], 'external': [], 'missing': []}
        except Exception as e:
            logger.error(f"Response parsing error: {e}")
            return {'internal': [], 'external': [], 'missing': []}
    
    def _validate_and_filter_relationships(self, raw_data: Dict[str, List], 
                                         entity: Dict, all_entities: List[Dict]) -> Dict[str, List]:
        """
        Waliduj i filtruj relacje używając RelationshipValidator
        """
        validation_results = []
        
        # Waliduj relacje wewnętrzne
        valid_internal = []
        for rel in raw_data.get('internal', []):
            is_valid, reason = self.validator.validate_internal_relationship(rel, entity, all_entities)
            validation_results.append((is_valid, reason))
            
            if is_valid:
                # Dodaj source_entity do relacji
                rel['source_entity'] = entity.get('name', '')
                valid_internal.append(rel)
            else:
                logger.debug(f"Rejected internal relation for {entity.get('name', '')}: {reason}")
        
        # Waliduj relacje zewnętrzne
        valid_external = []
        for rel in raw_data.get('external', []):
            is_valid, reason = self.validator.validate_external_relationship(rel)
            validation_results.append((is_valid, reason))
            
            if is_valid:
                # Dodaj entity do relacji
                rel['entity'] = entity.get('name', '')
                valid_external.append(rel)
            else:
                logger.debug(f"Rejected external relation for {entity.get('name', '')}: {reason}")
        
        # Waliduj brakujące encje
        valid_missing = []
        for missing in raw_data.get('missing', []):
            is_valid, reason = self.validator.validate_pending_entity(missing)
            validation_results.append((is_valid, reason))
            
            if is_valid:
                valid_missing.append(missing)
            else:
                logger.debug(f"Rejected missing entity for {entity.get('name', '')}: {reason}")
        
        # Aktualizuj statystyki
        raw_total = len(raw_data.get('internal', [])) + len(raw_data.get('external', [])) + len(raw_data.get('missing', []))
        valid_total = len(valid_internal) + len(valid_external) + len(valid_missing)
        
        self.stats["found_raw"] += raw_total
        self.stats["found_valid"] += valid_total
        self.stats["rejected"] += raw_total - valid_total
        
        return {
            'internal': valid_internal,
            'external': valid_external,
            'missing': valid_missing
        }
    
    def extract_for_entity(self, entity: Dict, context: List[str], text_sample: str, 
                          all_entities: List[Dict] = None) -> Dict:
        """
        Extract and validate relationships for one entity
        """
        try:
            entity_name = entity.get('name', '')
            
            # Build prompt
            prompt = NERPrompts.get_relationship_extraction_prompt(
                entity_name, entity.get('type', ''), context, text_sample
            )
            
            # Call LLM and parse
            response = self._call_llm(prompt)
            raw_data = self._parse_response(response)
            
            # Validate and filter relationships
            if all_entities is None:
                all_entities = []
            
            validated_data = self._validate_and_filter_relationships(raw_data, entity, all_entities)
            
            logger.info(f"Entity {entity_name}: {len(validated_data['internal'])} internal, "
                       f"{len(validated_data['external'])} external, "
                       f"{len(validated_data['missing'])} missing entities")
            
            return {
                'entity_name': entity_name,
                'entity_type': entity.get('type', ''),
                'internal_relationships': validated_data['internal'],
                'external_relationships': validated_data['external'],
                'missing_entities': validated_data['missing']
            }
            
        except Exception as e:
            logger.error(f"Failed for entity {entity.get('name', '')}: {e}")
            self.stats["failed"] += 1
            return {
                'entity_name': entity.get('name', ''),
                'entity_type': entity.get('type', ''),
                'internal_relationships': [],
                'external_relationships': [],
                'missing_entities': []
            }
    
    def extract_relationships(self, entities: List[Dict], original_text: str) -> List[Dict]:
        """
        Extract and validate relationships for all entities
        """
        if not entities:
            logger.warning("No entities provided for relationship extraction")
            return []
        
        # Prepare context
        entity_names = [e.get('name', '') for e in entities if e.get('name')]
        text_sample = self._prepare_text_sample(original_text)
        
        logger.info(f"Starting relationship extraction for {len(entities)} entities")
        
        results = []
        for i, entity in enumerate(entities):
            entity_name = entity.get('name', '')
            
            # Get context without current entity
            context = [name for name in entity_names if name != entity_name]
            
            # Extract relationships with validation
            result = self.extract_for_entity(entity, context, text_sample, entities)
            results.append(result)
            
            self.stats["processed"] += 1
            
            # Log progress every 5 entities
            if (i + 1) % 5 == 0:
                logger.info(f"Processed {i + 1}/{len(entities)} entities. "
                           f"Valid/Raw: {self.stats['found_valid']}/{self.stats['found_raw']}")
        
        # Final stats
        validation_rate = (self.stats['found_valid'] / self.stats['found_raw'] 
                          if self.stats['found_raw'] > 0 else 0)
        
        logger.info(f"Relationship extraction complete: {self.stats['processed']} entities, "
                   f"{self.stats['found_valid']} valid relationships "
                   f"({validation_rate:.1%} validation rate)")
        
        return results
    
    def _prepare_text_sample(self, original_text: str, max_length: int = 1500) -> str:
        """
        Prepare text sample for relationship extraction
        """
        if len(original_text) <= max_length:
            return original_text
        
        # Take first part and last part to give context
        half_length = max_length // 2
        start_part = original_text[:half_length]
        end_part = original_text[-half_length:]
        
        return f"{start_part}\n\n[...]\n\n{end_part}"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get extraction and validation statistics"""
        stats = self.stats.copy()
        
        if stats["found_raw"] > 0:
            stats["validation_rate"] = stats["found_valid"] / stats["found_raw"]
            stats["rejection_rate"] = stats["rejected"] / stats["found_raw"]
        else:
            stats["validation_rate"] = 0
            stats["rejection_rate"] = 0
        
        return stats
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            "processed": 0, 
            "found_raw": 0, 
            "found_valid": 0,
            "rejected": 0,
            "failed": 0
        }