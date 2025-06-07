"""
NER Graph Aggregator - Entity file management (bez relacji)
Handles entity persistence, indexing, and simple aggregation
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Local imports
from .utils import (
    load_ner_config, 
    log_memory_usage, 
    generate_entity_id,
    safe_filename,
    validate_file_exists
)


class AggregatorError(Exception):
    """Graph aggregation error"""
    pass


class GraphAggregator:
    """
    Manage entity files and build simple aggregated graphs (bez relacji)
    """
    
    def __init__(self, entities_dir: str = "entities", config_path: str = "ner/ner_config.json"):
        self.entities_dir = Path(entities_dir)
        self.entities_dir.mkdir(exist_ok=True)
        self.config = load_ner_config(config_path)
        self.entity_index = {}  # name -> entity_id mapping
        self.aggregation_stats = {
            "entities_created": 0,
            "entities_updated": 0,
            "duplicates_merged": 0,
            "files_written": 0
        }
    
    def load_entity_index(self):
        """Load existing entity index from files"""
        log_memory_usage("Loading entity index")
        
        self.entity_index = {}
        entity_files = list(self.entities_dir.glob("ent.*.json"))
        
        loaded_count = 0
        for entity_file in entity_files:
            try:
                with open(entity_file, 'r', encoding='utf-8') as f:
                    entity = json.load(f)
                    
                name_key = entity.get('name', '').lower().strip()
                if name_key:
                        self.entity_index[name_key] = entity['id']
                        loaded_count += 1
                        
            except Exception as e:
                print(f"Warning: Could not load {entity_file}: {e}")
        
        print(f"Loaded {loaded_count} entities from {len(entity_files)} files")
        log_memory_usage(f"Entity index loaded: {loaded_count} entities")
    
    def find_existing_entity(self, name: str) -> Optional[str]:
        """Find existing entity by name"""
        name_key = name.lower().strip()
        return self.entity_index.get(name_key)
    
    def create_entity_file(self, entity_data: Dict[str, Any], chunk_refs: List[str]) -> Optional[str]:
        """
        Create or update individual entity JSON file (bez relacji)
        
        Args:
            entity_data: Complete entity dictionary
            chunk_refs: List of chunk reference strings
            
        Returns:
            Entity ID if successful, None if failed
        """
        try:
            entity_name = entity_data.get('name', '')
            entity_type = entity_data.get('type', '')
            
            if not entity_name or not entity_type:
                print(f"Warning: Invalid entity data - missing name or type")
                return None
            
            # Check for existing entity
            existing_id = self.find_existing_entity(entity_name)
            
            if existing_id:
                # Update existing entity
                entity_id = existing_id
                print(f"Entity '{entity_name}' already exists as {existing_id}, updating...")
                self._update_existing_entity(entity_id, entity_data, chunk_refs)
                self.aggregation_stats["entities_updated"] += 1
            else:
                # Create new entity
                entity_id = entity_data.get('id') or generate_entity_id(entity_name, entity_type)
                entity_data['id'] = entity_id
                self._create_new_entity(entity_id, entity_data, chunk_refs)
                self.aggregation_stats["entities_created"] += 1
            
            # Update index
            name_key = entity_name.lower().strip()
            self.entity_index[name_key] = entity_id
            
            return entity_id
            
        except Exception as e:
            print(f"Error creating/updating entity {entity_data.get('name', 'unknown')}: {e}")
            return None
    
    def _create_new_entity(self, entity_id: str, entity_data: Dict[str, Any], chunk_refs: List[str]):
        """Create new entity file (bez relacji)"""
        # Ensure proper structure
        complete_entity = {
            "id": entity_id,
            "name": entity_data.get('name', ''),
            "type": entity_data.get('type', ''),
            "description": entity_data.get('description', ''),
            "confidence": entity_data.get('confidence', 0.5),
            
            "source_info": {
                "evidence": entity_data.get('source_info', {}).get('evidence', ''),
                "chunk_references": chunk_refs,
                "found_in_chunks": entity_data.get('source_info', {}).get('found_in_chunks', []),
                "source_document": entity_data.get('source_info', {}).get('source_document', 'unknown')
            },
            
            "metadata": {
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "model_used": entity_data.get('metadata', {}).get('model_used', 'unknown'),
                "extraction_method": entity_data.get('metadata', {}).get('extraction_method', 'unknown')
            }
        }
        
        # Save to file
        entity_file = self.entities_dir / f"{entity_id}.json"
        self._write_entity_file(entity_file, complete_entity)
        
        print(f"Created entity file: {entity_file}")
    
    def _update_existing_entity(self, entity_id: str, new_data: Dict[str, Any], chunk_refs: List[str]):
        """Update existing entity file (bez relacji)"""
        entity_file = self.entities_dir / f"{entity_id}.json"
        
        if not entity_file.exists():
            print(f"Warning: Entity file {entity_file} not found, creating new")
            self._create_new_entity(entity_id, new_data, chunk_refs)
            return
        
        try:
            # Load existing entity
            with open(entity_file, 'r', encoding='utf-8') as f:
                existing_entity = json.load(f)
            
            # Merge data
            updated_entity = self._merge_entity_data(existing_entity, new_data, chunk_refs)
            
            # Save updated entity
            self._write_entity_file(entity_file, updated_entity)
            
            print(f"Updated entity file: {entity_file}")
            
        except Exception as e:
            print(f"Error updating entity {entity_id}: {e}")
    
    def _merge_entity_data(self, existing: Dict[str, Any], new_data: Dict[str, Any], 
                          chunk_refs: List[str]) -> Dict[str, Any]:
        """Merge new entity data with existing entity (bez relacji)"""
        # Start with existing data
        merged = existing.copy()
        
        # Update confidence if new is higher
        new_confidence = new_data.get('confidence', 0)
        if new_confidence > merged.get('confidence', 0):
            merged['confidence'] = new_confidence
        
        # Merge descriptions (keep longer one)
        new_desc = new_data.get('description', '')
        if len(new_desc) > len(merged.get('description', '')):
            merged['description'] = new_desc
        
        # Merge source info
        source_info = merged.setdefault('source_info', {})
        
        # Add new chunk references
        existing_refs = set(source_info.get('chunk_references', []))
        existing_refs.update(chunk_refs)
        source_info['chunk_references'] = list(existing_refs)
        
        # Add new chunks
        existing_chunks = set(source_info.get('found_in_chunks', []))
        new_chunks = set(new_data.get('source_info', {}).get('found_in_chunks', []))
        existing_chunks.update(new_chunks)
        source_info['found_in_chunks'] = list(existing_chunks)
        
        # Update metadata
        merged['metadata']['last_updated'] = datetime.now().isoformat()
        
        return merged
    
    def _write_entity_file(self, file_path: Path, entity_data: Dict[str, Any]):
        """Write entity data to file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(entity_data, f, indent=2, ensure_ascii=False)
            self.aggregation_stats["files_written"] += 1
        except Exception as e:
            raise AggregatorError(f"Failed to write entity file {file_path}: {e}")
    
    def create_symbol_index(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create symbol index: name -> entity IDs mapping
        
        Args:
            entities: List of all entities
            
        Returns:
            Symbol index with statistics
        """
        symbols = {}
        name_variants = {}  # Track name variations
        
        for entity in entities:
            name = entity.get('name', '').strip()
            entity_id = entity.get('id', '')
            entity_type = entity.get('type', '')
            
            if not name or not entity_id:
                continue
            
            # Normalize name for grouping
            name_lower = name.lower()
            name_clean = name_lower.replace('a', '').replace('y', '').replace('i', '')  # Simple Polish declension
            
            # Add to symbols index
            if name_lower not in symbols:
                symbols[name_lower] = []
            symbols[name_lower].append({
                "entity_id": entity_id,
                "original_name": name,
                "type": entity_type,
                "confidence": entity.get('confidence', 0.5)
            })
            
            # Track name variations for deduplication
            if name_clean not in name_variants:
                name_variants[name_clean] = []
            name_variants[name_clean].append({
                "name": name,
                "name_lower": name_lower,
                "entity_id": entity_id
            })
        
        # Find potential duplicates
        duplicates = {}
        for clean_name, variants in name_variants.items():
            if len(variants) > 1:
                duplicates[clean_name] = variants
        
        return {
            "symbols": symbols,
            "duplicates_detected": duplicates,
            "total_unique_names": len(symbols),
            "potential_duplicates": len(duplicates)
        }

    def create_aggregated_graph(self, output_file: str = "knowledge_graph.json") -> Dict[str, Any]:
        """
        Create aggregated knowledge graph from all entity files (bez relacji)
        
        Args:
            output_file: Output file name for aggregated graph
            
        Returns:
            Aggregated graph statistics
        """
        log_memory_usage("Creating aggregated graph")
        
        entities = []
        entity_files = list(self.entities_dir.glob("ent.*.json"))
        
        # Load all entities
        for entity_file in entity_files:
            try:
                with open(entity_file, 'r', encoding='utf-8') as f:
                    entity = json.load(f)
                    entities.append(entity)
            except Exception as e:
                print(f"Warning: Could not load {entity_file}: {e}")
        
        # Create symbol index
        symbol_data = self.create_symbol_index(entities)
        
        # Create aggregated graph
        aggregated_graph = {
            "metadata": {
                "created": datetime.now().isoformat(),
                "total_entities": len(entities),
                "source_directory": str(self.entities_dir),
                "aggregation_stats": self.aggregation_stats
            },
            "entities": entities,
            "symbols": symbol_data["symbols"],
            "duplicates": symbol_data["duplicates_detected"],
            "summary": self._generate_graph_summary(entities)
        }
        
        # Add symbol stats to summary
        aggregated_graph["summary"]["symbol_stats"] = {
            "unique_names": symbol_data["total_unique_names"],
            "potential_duplicates": symbol_data["potential_duplicates"]
        }
        
        # Save aggregated graph
        output_path = Path(output_file)
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(aggregated_graph, f, indent=2, ensure_ascii=False)
            
            print(f"Aggregated graph saved: {output_path}")
            print(f"Symbol index: {symbol_data['total_unique_names']} unique names")
            if symbol_data['potential_duplicates'] > 0:
                print(f"⚠️  Found {symbol_data['potential_duplicates']} potential duplicate groups")
            
            log_memory_usage("Aggregated graph created")
            
            return {
                "entities_aggregated": len(entities),
                "output_file": str(output_path),
                "file_size_mb": output_path.stat().st_size / (1024 * 1024),
                "creation_time": datetime.now().isoformat(),
                "symbol_stats": symbol_data
            }
            
        except Exception as e:
            raise AggregatorError(f"Failed to save aggregated graph: {e}")
    
    def _generate_graph_summary(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for the graph (bez relacji)"""
        if not entities:
            return {"total_entities": 0}
        
        # Count by type
        entity_types = {}
        confidence_scores = []
        
        for entity in entities:
            # Count types
            entity_type = entity.get('type', 'unknown')
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
            
            # Collect confidence scores
            confidence = entity.get('confidence', 0)
            if isinstance(confidence, (int, float)):
                confidence_scores.append(confidence)
        
        # Calculate confidence statistics
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        return {
            "total_entities": len(entities),
            "entity_types": entity_types,
            "avg_confidence": round(avg_confidence, 3),
            "confidence_range": {
                "min": min(confidence_scores) if confidence_scores else 0,
                "max": max(confidence_scores) if confidence_scores else 0
            }
        }
    
    def get_aggregation_stats(self) -> Dict[str, Any]:
        """Get aggregation statistics"""
        return {
            **self.aggregation_stats,
            "entities_dir": str(self.entities_dir),
            "index_size": len(self.entity_index),
            "config": {
                "entities_directory": str(self.entities_dir)
            }
        }
    
    def reset_stats(self):
        """Reset aggregation statistics"""
        self.aggregation_stats = {
            "entities_created": 0,
            "entities_updated": 0,
            "duplicates_merged": 0,
            "files_written": 0
        }