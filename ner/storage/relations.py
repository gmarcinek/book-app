# ner/storage/relations.py

"""
Relationship discovery and management using NetworkX knowledge graph
"""

import logging
from typing import Dict, List, Tuple, Set, Optional, Any

import networkx as nx

from .models import StoredEntity, StoredChunk, EntityRelationship, RelationType

logger = logging.getLogger(__name__)


class RelationshipManager:
   """
   Manages structural and semantic relationships in knowledge graph
   """
   
   def __init__(self):
       self.graph = nx.MultiDiGraph()
       logger.info("🔗 RelationshipManager initialized")
   
   def add_chunk_entity_relationships(self, chunk: StoredChunk, entity_ids: List[str]) -> List[EntityRelationship]:
       """Add structural relationships between chunk and its entities"""
       relationships = []
       
       if not self.graph.has_node(chunk.id):
           self.graph.add_node(chunk.id, type='chunk', data=chunk.to_dict_for_json())
       
       for entity_id in entity_ids:
           relationship = EntityRelationship(
               source_id=chunk.id,
               target_id=entity_id,
               relation_type=RelationType.CONTAINS,
               confidence=1.0,
               evidence=chunk.get_text_preview(200),
               source_chunk_id=chunk.id,
               discovery_method="structural"
           )
           
           self._add_relationship_to_graph(relationship)
           relationships.append(relationship)
       
       logger.debug(f"🔗 Added {len(relationships)} relationships for chunk {chunk.id}")
       return relationships
   
   def add_entity_node(self, entity: StoredEntity) -> bool:
       """Add entity node to graph"""
       try:
           self.graph.add_node(entity.id, type='entity', data=entity.to_dict_for_json())
           return True
       except Exception as e:
           logger.error(f"❌ Failed to add entity node {entity.id}: {e}")
           return False
   
   def add_structural_relationship(self, source_id: str, target_id: str, rel_type: str, 
                                 confidence: float = 1.0, **metadata) -> bool:
       """Add structural relationship between entities - FIXED"""
       try:
           # Extract discovery_method from metadata if present
           discovery_method = metadata.pop('discovery_method', 'structural')
           
           relationship = EntityRelationship(
                source_id=source_id,
                target_id=target_id,
                relation_type=rel_type,
                confidence=confidence,
                evidence=metadata.get('evidence', ''),  # ← Mapuj evidence na evidence
                discovery_method=discovery_method
            )
           self._add_relationship_to_graph(relationship)
           return True
       except Exception as e:
           logger.error(f"❌ Failed to add structural relationship: {e}")
           return False
   
   def discover_structural_relationships(self, entities: Dict[str, StoredEntity], chunks: Dict[str, StoredChunk]) -> List[EntityRelationship]:
       """Discover basic structural relationships"""
       relationships = []
       
       # Basic scene participation discovery
       for chunk_id, chunk in chunks.items():
           for entity_id in chunk.entity_ids:
               if entity_id in entities:
                   entity = entities[entity_id]
                   if entity.type in ['SCENA', 'LOKACJA', 'OSOBA']:
                       relationships.extend(self._discover_scene_relationships(entity, chunk))
       
       logger.info(f"🔍 Discovered {len(relationships)} structural relationships")
       return relationships
   
   def add_semantic_relationships(self, entity_id: str, semantic_description: str):
       """Add semantic relationships as natural language description"""
       if self.graph.has_node(entity_id):
           if 'semantic_relations' not in self.graph.nodes[entity_id]:
               self.graph.nodes[entity_id]['semantic_relations'] = []
           self.graph.nodes[entity_id]['semantic_relations'].append(semantic_description)
   
   def get_entity_relationships(self, entity_id: str) -> List[Dict[str, Any]]:
       """Get all relationships for an entity"""
       relationships = []
       
       if not self.graph.has_node(entity_id):
           return relationships
       
       # Outgoing relationships
       for target in self.graph.successors(entity_id):
           for edge_data in self.graph[entity_id][target].values():
               relationships.append({
                   'source': entity_id,
                   'target': target,
                   'direction': 'outgoing',
                   **edge_data
               })
       
       # Incoming relationships
       for source in self.graph.predecessors(entity_id):
           for edge_data in self.graph[source][entity_id].values():
               relationships.append({
                   'source': source,
                   'target': entity_id,
                   'direction': 'incoming',
                   **edge_data
               })
       
       return relationships
   
   def get_related_entities(self, entity_id: str, max_depth: int = 2) -> List[str]:
       """Get entities related to given entity within max_depth"""
       if not self.graph.has_node(entity_id):
           return []
       
       try:
           related = set()
           current_level = {entity_id}
           
           for depth in range(max_depth):
               next_level = set()
               
               for node in current_level:
                   neighbors = set(self.graph.successors(node)) | set(self.graph.predecessors(node))
                   
                   for neighbor in neighbors:
                       if (neighbor not in related and 
                           neighbor != entity_id and
                           self.graph.nodes[neighbor].get('type') == 'entity'):
                           related.add(neighbor)
                           next_level.add(neighbor)
               
               current_level = next_level
               if not current_level:
                   break
           
           return list(related)
           
       except Exception as e:
           logger.error(f"❌ Failed to get related entities for {entity_id}: {e}")
           return []
   
   def export_graph_data(self) -> Dict[str, Any]:
       """Export graph data for visualization and analysis"""
       nodes = []
       edges = []
       
       for node_id, node_data in self.graph.nodes(data=True):
           nodes.append({
               'id': node_id,
               'type': node_data.get('type', 'unknown'),
               **node_data.get('data', {})
           })
       
       for source, target, edge_data in self.graph.edges(data=True):
           edges.append({
               'source': source,
               'target': target,
               **edge_data
           })
       
       return {
           'nodes': nodes,
           'edges': edges,
           'stats': {
               'node_count': self.graph.number_of_nodes(),
               'edge_count': self.graph.number_of_edges(),
               'entity_count': len([n for n, d in self.graph.nodes(data=True) if d.get('type') == 'entity']),
               'chunk_count': len([n for n, d in self.graph.nodes(data=True) if d.get('type') == 'chunk'])
           }
       }
   
   def get_relationship_stats(self) -> Dict[str, Any]:
       """Get statistics about relationships in the graph"""
       from collections import Counter
       
       relationship_counts = Counter()
       for _, _, edge_data in self.graph.edges(data=True):
           rel_type = edge_data.get('relation_type', 'unknown')
           relationship_counts[rel_type] += 1
       
       return {
           'total_relationships': self.graph.number_of_edges(),
           'relationship_types': dict(relationship_counts)
       }
   
   def _discover_scene_relationships(self, entity: StoredEntity, chunk: StoredChunk) -> List[EntityRelationship]:
       """Discover basic scene participation relationships"""
       relationships = []
       
       if entity.type == 'OSOBA':
           relationship = EntityRelationship(
               source_id=entity.id,
               target_id=chunk.id,
               relation_type=RelationType.MENTIONED_WITH,
               confidence=0.8,
               source_chunk_id=chunk.id,
               discovery_method="scene_participation"
           )
           relationships.append(relationship)
       
       return relationships
   
   def _add_relationship_to_graph(self, relationship: EntityRelationship):
       """Add relationship to NetworkX graph"""
       self.graph.add_edge(
           relationship.source_id,
           relationship.target_id,
           key=relationship.get_relationship_key(),
           **relationship.to_dict()
       )