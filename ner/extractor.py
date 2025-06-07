"""
NER Entity Extractor - Ulepszony ekstraktor z lepszą walidacją
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
from .prompts import NERPrompts
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
    chunk_id: Optional[int] = None
    context: Optional[str] = None


class EntityExtractor:
    """
    Ulepszony ekstraktor encji z lepszą walidacją i filtrowaniem
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
        """Build entity extraction prompt using centralized prompts"""
        return NERPrompts.get_entity_extraction_prompt(text)
    
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
        """Parse LLM JSON response into entities list with better error handling"""
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
        Validate and clean entity data
        
        Returns:
            Cleaned entity dict or None if invalid
        """
        # Check required fields
        if not isinstance(entity_data, dict):
            return None
        
        name = entity_data.get('name', '').strip()
        entity_type = entity_data.get('type', '').strip().upper()
        
        if not name or not entity_type:
            logger.debug(f"Missing name or type: {entity_data}")
            return None
        
        # Validate name
        if not validate_entity_name(name):
            logger.debug(f"Invalid entity name: '{name}'")
            return None
        
        # Validate type
        if entity_type not in ENTITY_TYPES:
            logger.debug(f"Invalid entity type: '{entity_type}' (valid types: {ENTITY_TYPES})")
            return None
        
        # Clean and validate description
        description = str(entity_data.get('description', '')).strip()
        if len(description) > 200:  # Limit description length
            description = description[:200] + "..."
        
        # Validate and normalize confidence
        confidence = entity_data.get('confidence', 0.5)
        try:
            confidence = float(confidence)
            confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1 range
        except (ValueError, TypeError):
            confidence = 0.5
        
        # Reject entities with very low confidence
        if confidence < 0.3:
            logger.debug(f"Rejected low confidence entity: {name} ({confidence})")
            return None
        
        return {
            'name': name,
            'type': entity_type,
            'description': description,
            'confidence': confidence
        }
    
    def _extract_entities_from_chunk(self, chunk: TextChunk) -> List[ExtractedEntity]:
        """Extract and validate entities from a single text chunk"""
        try:
            # Build prompt
            prompt = self._build_extraction_prompt(chunk.text)
            
            # Call LLM
            response = self._call_llm(prompt)
            
            # Parse response
            raw_entities = self._parse_llm_response(response)
            self.extraction_stats["entities_extracted_raw"] += len(raw_entities)
            
            # Validate and convert to ExtractedEntity objects
            valid_entities = []
            for entity_data in raw_entities:
                cleaned_entity = self._validate_and_clean_entity(entity_data)
                
                if cleaned_entity:
                    entity = ExtractedEntity(
                        name=cleaned_entity['name'],
                        type=cleaned_entity['type'],
                        description=cleaned_entity['description'],
                        confidence=cleaned_entity['confidence'],
                        chunk_id=chunk.id,
                        context=chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text
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
        Remove duplicate entities based on normalized names
        Keep the entity with highest confidence
        """
        if not entities:
            return entities
        
        # Group entities by normalized name
        entity_groups = {}
        for entity in entities:
            normalized_name = entity.name.lower().strip()
            
            if normalized_name not in entity_groups:
                entity_groups[normalized_name] = []
            entity_groups[normalized_name].append(entity)
        
        # Keep best entity from each group
        deduplicated = []
        duplicates_removed = 0
        
        for normalized_name, group in entity_groups.items():
            if len(group) == 1:
                deduplicated.append(group[0])
            else:
                # Keep entity with highest confidence
                best_entity = max(group, key=lambda e: e.confidence)
                deduplicated.append(best_entity)
                duplicates_removed += len(group) - 1
                
                logger.debug(f"Deduplicated '{normalized_name}': kept 1 of {len(group)} entities")
        
        if duplicates_removed > 0:
            logger.info(f"Removed {duplicates_removed} duplicate entities")
        
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
        
        logger.info(f"Entity extraction complete:")
        logger.info(f"  Chunks processed: {self.extraction_stats['chunks_processed']}")
        logger.info(f"  Raw entities: {self.extraction_stats['entities_extracted_raw']}")
        logger.info(f"  Valid entities: {self.extraction_stats['entities_extracted_valid']}")
        logger.info(f"  Final entities (after dedup): {len(deduplicated_entities)}")
        logger.info(f"  Validation rate: {validation_rate:.1%}")
        
        return deduplicated_entities
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get detailed extraction statistics"""
        stats = self.extraction_stats.copy()
        
        if stats["entities_extracted_raw"] > 0:
            stats["validation_rate"] = stats["entities_extracted_valid"] / stats["entities_extracted_raw"]
            stats["rejection_rate"] = stats["entities_rejected"] / stats["entities_extracted_raw"]
        else:
            stats["validation_rate"] = 0
            stats["rejection_rate"] = 0
        
        return stats