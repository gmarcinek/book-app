"""
ner/storage/models.py

Data models for semantic storage - entities, chunks, and relationships
"""

import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict


@dataclass
class StoredEntity:
    """Entity stored in semantic store with dual embeddings"""
    id: str
    name: str
    type: str
    description: str
    confidence: float
    aliases: List[str] = field(default_factory=list)
    context: str = ""
    
    # Dual embeddings for different matching strategies
    name_embedding: Optional[np.ndarray] = None      # Fast semantic matching
    context_embedding: Optional[np.ndarray] = None   # Contextual discovery
    
    # Source tracking
    source_chunk_ids: List[str] = field(default_factory=list)
    document_sources: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    merge_count: int = 0  # How many times this entity was merged
    
    def update_timestamp(self):
        """Update the modification timestamp"""
        self.updated_at = datetime.now().isoformat()
    
    def add_source_chunk(self, chunk_id: str):
        """Add chunk reference if not already present"""
        if chunk_id not in self.source_chunk_ids:
            self.source_chunk_ids.append(chunk_id)
            self.update_timestamp()
    
    def add_document_source(self, document_path: str):
        """Add document source if not already present"""
        if document_path not in self.document_sources:
            self.document_sources.append(document_path)
            self.update_timestamp()
    
    def merge_aliases(self, new_aliases: List[str]) -> List[str]:
        """Merge new aliases, return newly discovered ones"""
        discovered = []
        existing_lower = {alias.lower() for alias in self.aliases}
        name_lower = self.name.lower()
        
        for alias in new_aliases:
            alias_clean = alias.strip()
            if (alias_clean and 
                alias_clean.lower() not in existing_lower and 
                alias_clean.lower() != name_lower):
                self.aliases.append(alias_clean)
                discovered.append(alias_clean)
                existing_lower.add(alias_clean.lower())
        
        if discovered:
            self.merge_count += 1
            self.update_timestamp()
        
        return discovered
    
    def to_dict_for_json(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization (excluding embeddings)"""
        data = asdict(self)
        # Remove numpy arrays for JSON serialization
        data.pop('name_embedding', None)
        data.pop('context_embedding', None)
        return data
    
    def get_semantic_text_for_name(self) -> str:
        """Get text for name embedding generation"""
        return f"{self.name} {self.type}"
    
    def get_semantic_text_for_context(self) -> str:
        """Get text for context embedding generation"""
        return f"{self.name} {self.type} {self.description} {self.context}"


@dataclass
class StoredChunk:
    """Chunk stored in semantic store"""
    id: str
    text: str
    document_source: str
    start_pos: int = 0
    end_pos: int = 0
    
    # Embedding for contextual similarity
    text_embedding: Optional[np.ndarray] = None
    
    # Entity tracking
    entity_ids: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    processed_at: Optional[str] = None  # When NER was completed
    
    def add_entity(self, entity_id: str):
        """Add entity reference if not already present"""
        if entity_id not in self.entity_ids:
            self.entity_ids.append(entity_id)
    
    def mark_processed(self):
        """Mark chunk as NER-processed"""
        self.processed_at = datetime.now().isoformat()
    
    def to_dict_for_json(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization (excluding embedding)"""
        data = asdict(self)
        # Remove numpy array for JSON serialization
        data.pop('text_embedding', None)
        return data
    
    def get_text_preview(self, max_length: int = 100) -> str:
        """Get truncated text preview for logging"""
        if len(self.text) <= max_length:
            return self.text
        return self.text[:max_length] + "..."


@dataclass
class EntityRelationship:
    """Relationship between entities or between chunk and entity"""
    source_id: str
    target_id: str
    relation_type: str
    confidence: float = 1.0
    
    # Context information
    evidence_text: str = ""  # Text supporting this relationship
    source_chunk_id: Optional[str] = None  # Where this relationship was discovered
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    discovery_method: str = "unknown"  # How this relationship was found
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return asdict(self)
    
    def get_relationship_key(self) -> str:
        """Get unique key for this relationship"""
        return f"{self.source_id}--{self.relation_type}--{self.target_id}"


# Relationship types constants - CLEANED UP
class RelationType:
    """Standard relationship types - only essential ones"""
    # Structural relationships
    CONTAINS = "contains"           # chunk contains entity
    
    # Semantic relationships  
    SIMILAR_TO = "similar_to"      # entities are semantically similar

# Utility functions for model operations
def create_entity_id(name: str, entity_type: str) -> str:
    """Generate unique entity ID"""
    import hashlib
    import time
    
    timestamp = str(int(time.time() * 1000000))
    hash_input = f"{name}_{entity_type}_{timestamp}"
    hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    return f"sem.{timestamp}.{hash_suffix}"


def create_chunk_id(document_source: str, chunk_index: int) -> str:
    import hashlib
    import time
    
    timestamp = int(time.time() * 1000)  # milliseconds
    safe_doc = document_source.replace('/', '_').replace('\\', '_')
    hash_input = f"{safe_doc}_{chunk_index}_{timestamp}"
    hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    return f"chunk.{timestamp}.{chunk_index}.{hash_suffix}"