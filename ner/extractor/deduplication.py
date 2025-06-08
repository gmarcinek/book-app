"""
Deduplikacja encji: _deduplicate_entities() (aliases, confidence)
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


def _deduplicate_entities(entities: List) -> List:
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