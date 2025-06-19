"""
Entity Linker - Maps entity names to IDs for relationship processing
"""

import logging
from typing import Optional, Dict, List
from ..storage import SemanticStore

logger = logging.getLogger(__name__)


class EntityLinker:
    """Maps entity names from LLM relationships to actual entity IDs"""
    
    def __init__(self, semantic_store: SemanticStore = None):
        self.semantic_store = semantic_store
        self._name_to_id_cache = {}
        
    def resolve_entity_name(self, name: str) -> Optional[str]:
        """
        Resolve entity name to entity ID
        
        Args:
            name: Entity name from LLM relationship
            
        Returns:
            Entity ID if found, None otherwise
        """
        if not self.semantic_store:
            return None
            
        name_clean = name.strip()
        
        # Check cache first
        if name_clean in self._name_to_id_cache:
            return self._name_to_id_cache[name_clean]
        
        # 1. Exact name match
        entity_id = self._exact_name_match(name_clean)
        if entity_id:
            self._name_to_id_cache[name_clean] = entity_id
            return entity_id
        
        # 2. Alias match
        entity_id = self._alias_match(name_clean)
        if entity_id:
            self._name_to_id_cache[name_clean] = entity_id
            return entity_id
        
        # 3. Embedding similarity fallback
        entity_id = self._similarity_match(name_clean)
        if entity_id:
            self._name_to_id_cache[name_clean] = entity_id
            return entity_id
        
        logger.debug(f"⚠️ Entity '{name_clean}' not found")
        return None
    
    def resolve_relationship(self, relationship: Dict) -> Optional[Dict]:
        """
        Resolve relationship with entity IDs
        
        Args:
            relationship: Raw relationship with names
            
        Returns:
            Relationship with entity IDs if both source/target found
        """
        source_id = self.resolve_entity_name(relationship['source'])
        target_id = self.resolve_entity_name(relationship['target'])
        
        if source_id and target_id:
            return {
                'source_id': source_id,
                'target_id': target_id,
                'pattern': relationship['pattern'],
                'evidence': relationship.get('evidence', ''),
                'confidence': relationship.get('confidence', 0.8)
            }
        
        return None
    
    def _exact_name_match(self, name: str) -> Optional[str]:
        """Find entity by exact name match"""
        for entity_id, entity in self.semantic_store.entities.items():
            if entity.name.lower() == name.lower():
                return entity_id
        return None
    
    def _alias_match(self, name: str) -> Optional[str]:
        """Find entity by alias match"""
        name_lower = name.lower()
        for entity_id, entity in self.semantic_store.entities.items():
            for alias in entity.aliases:
                if alias.lower() == name_lower:
                    return entity_id
        return None
    
    def _similarity_match(self, name: str) -> Optional[str]:
        """Find entity by embedding similarity (fallback)"""
        try:
            # Use semantic store's search with lower threshold
            search_results = self.semantic_store.search_entities_by_name(name, max_results=1)
            
            if search_results and search_results[0][1] >= 0.7:  # Similarity threshold
                entity = search_results[0][0]
                return entity.id
                
        except Exception as e:
            logger.debug(f"⚠️ Similarity search failed for '{name}': {e}")
        
        return None
    
    def clear_cache(self):
        """Clear the name-to-ID cache"""
        self._name_to_id_cache.clear()
    
    def get_stats(self) -> Dict:
        """Get linker statistics"""
        return {
            'cached_mappings': len(self._name_to_id_cache),
            'has_semantic_store': self.semantic_store is not None
        }