"""
ner/storage/relations.py

Relationship discovery and management using NetworkX knowledge graph
"""

import logging
import re
from typing import Dict, List, Tuple, Set, Optional, Any
from collections import defaultdict, Counter

import networkx as nx

from .models import StoredEntity, StoredChunk, EntityRelationship, RelationType

logger = logging.getLogger(__name__)


class RelationshipManager:
    """
    Discovers and manages relationships between entities and chunks
    
    Relationship Types:
    - Structural: chunk contains entity, entity part of entity
    - Co-occurrence: entities appear together frequently  
    - Semantic: entities are semantically similar
    - Domain-specific: location, authorship, character relationships
    """
    
    def __init__(self, 
                 co_occurrence_threshold: int = 2,
                 semantic_similarity_threshold: float = 0.7):
        """
        Initialize relationship manager
        
        Args:
            co_occurrence_threshold: Minimum co-occurrences to create relationship
            semantic_similarity_threshold: Minimum similarity for semantic relationships
        """
        self.graph = nx.MultiDiGraph()
        self.co_occurrence_threshold = co_occurrence_threshold
        self.semantic_similarity_threshold = semantic_similarity_threshold
        
        # Track co-occurrences for relationship discovery
        self.entity_co_occurrences: Dict[Tuple[str, str], int] = defaultdict(int)
        self.chunk_entity_map: Dict[str, Set[str]] = defaultdict(set)
        
        logger.info("🔗 RelationshipManager initialized")
    
    def add_chunk_entity_relationships(self, chunk: StoredChunk, entity_ids: List[str]) -> List[EntityRelationship]:
        """
        Add structural relationships between chunk and its entities
        
        Args:
            chunk: Chunk containing entities
            entity_ids: List of entity IDs found in chunk
            
        Returns:
            List of created relationships
        """
        relationships = []
        
        # Add chunk node if not exists
        if not self.graph.has_node(chunk.id):
            self.graph.add_node(chunk.id, 
                              type='chunk', 
                              data=chunk.to_dict_for_json())
        
        # Create CONTAINS relationships
        for entity_id in entity_ids:
            relationship = EntityRelationship(
                source_id=chunk.id,
                target_id=entity_id,
                relation_type=RelationType.CONTAINS,
                confidence=1.0,
                evidence_text=chunk.get_text_preview(200),
                source_chunk_id=chunk.id,
                discovery_method="structural"
            )
            
            self._add_relationship_to_graph(relationship)
            relationships.append(relationship)
            
            # Track for co-occurrence analysis
            self.chunk_entity_map[chunk.id].add(entity_id)
        
        # Discover co-occurrence relationships between entities in same chunk
        co_occur_relationships = self._discover_co_occurrence_relationships(entity_ids, chunk.id)
        relationships.extend(co_occur_relationships)
        
        logger.debug(f"🔗 Added {len(relationships)} relationships for chunk {chunk.id}")
        return relationships
    
    def add_entity_node(self, entity: StoredEntity) -> bool:
        """
        Add entity node to graph
        
        Args:
            entity: Entity to add
            
        Returns:
            True if successfully added
        """
        try:
            self.graph.add_node(entity.id,
                              type='entity',
                              data=entity.to_dict_for_json())
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add entity node {entity.id}: {e}")
            return False
    
    def discover_semantic_relationships(self, 
                                      entities: Dict[str, StoredEntity],
                                      embedder) -> List[EntityRelationship]:
        """
        Discover semantic relationships between entities using embeddings
        
        Args:
            entities: Dictionary of entities
            embedder: EntityEmbedder instance for similarity computation
            
        Returns:
            List of discovered semantic relationships
        """
        relationships = []
        entity_list = list(entities.values())
        
        logger.info(f"🔍 Discovering semantic relationships for {len(entity_list)} entities")
        
        # Compare each entity with every other entity
        for i, entity1 in enumerate(entity_list):
            if entity1.context_embedding is None:
                continue
                
            for j, entity2 in enumerate(entity_list):
                if i >= j or entity2.context_embedding is None:  # Avoid duplicates and self-comparison
                    continue
                
                # Skip if entities are already connected
                if self.graph.has_edge(entity1.id, entity2.id):
                    continue
                
                # Compute semantic similarity
                similarity = embedder.compute_similarity(
                    entity1.context_embedding, 
                    entity2.context_embedding
                )
                
                if similarity >= self.semantic_similarity_threshold:
                    # Create bidirectional semantic similarity relationship
                    relationship = EntityRelationship(
                        source_id=entity1.id,
                        target_id=entity2.id,
                        relation_type=RelationType.SIMILAR_TO,
                        confidence=similarity,
                        evidence_text=f"Semantic similarity: {similarity:.3f}",
                        discovery_method="semantic_embedding"
                    )
                    
                    self._add_relationship_to_graph(relationship)
                    relationships.append(relationship)
                    
                    # Add reverse relationship
                    reverse_relationship = EntityRelationship(
                        source_id=entity2.id,
                        target_id=entity1.id,
                        relation_type=RelationType.SIMILAR_TO,
                        confidence=similarity,
                        evidence_text=f"Semantic similarity: {similarity:.3f}",
                        discovery_method="semantic_embedding"
                    )
                    
                    self._add_relationship_to_graph(reverse_relationship)
                    relationships.append(reverse_relationship)
        
        logger.info(f"🔍 Discovered {len(relationships)} semantic relationships")
        return relationships
    
    def discover_domain_specific_relationships(self, 
                                             entities: Dict[str, StoredEntity],
                                             chunks: Dict[str, StoredChunk]) -> List[EntityRelationship]:
        """
        Discover domain-specific relationships using pattern matching
        
        Args:
            entities: Dictionary of entities
            chunks: Dictionary of chunks for context
            
        Returns:
            List of discovered domain relationships
        """
        relationships = []
        
        # Group entities by type for efficient processing
        entities_by_type = defaultdict(list)
        for entity in entities.values():
            entities_by_type[entity.type].append(entity)
        
        # Discover location relationships
        location_relationships = self._discover_location_relationships(
            entities_by_type, chunks
        )
        relationships.extend(location_relationships)
        
        # Discover authorship relationships
        authorship_relationships = self._discover_authorship_relationships(
            entities_by_type, chunks
        )
        relationships.extend(authorship_relationships)
        
        # Discover character-related relationships
        character_relationships = self._discover_character_relationships(
            entities_by_type, chunks
        )
        relationships.extend(character_relationships)
        
        logger.info(f"🎯 Discovered {len(relationships)} domain-specific relationships")
        return relationships
    
    def get_entity_relationships(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Get all relationships for an entity
        
        Args:
            entity_id: Entity ID to get relationships for
            
        Returns:
            List of relationship dictionaries
        """
        relationships = []
        
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
        """
        Get entities related to given entity within max_depth
        
        Args:
            entity_id: Entity ID to find related entities for
            max_depth: Maximum relationship depth to explore
            
        Returns:
            List of related entity IDs
        """
        if not self.graph.has_node(entity_id):
            return []
        
        try:
            # Use BFS to find related entities within max_depth
            related = set()
            current_level = {entity_id}
            
            for depth in range(max_depth):
                next_level = set()
                
                for node in current_level:
                    # Get neighbors (both directions)
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
    
    def _discover_co_occurrence_relationships(self, entity_ids: List[str], chunk_id: str) -> List[EntityRelationship]:
        """
        Discover co-occurrence relationships between entities in same chunk
        
        Args:
            entity_ids: Entity IDs that co-occur
            chunk_id: Chunk where co-occurrence happens
            
        Returns:
            List of co-occurrence relationships
        """
        relationships = []
        
        # Update co-occurrence counts
        for i, entity1_id in enumerate(entity_ids):
            for entity2_id in entity_ids[i+1:]:
                # Create sorted pair to avoid duplicates
                pair = tuple(sorted([entity1_id, entity2_id]))
                self.entity_co_occurrences[pair] += 1
                
                # Create relationship if threshold met
                if self.entity_co_occurrences[pair] >= self.co_occurrence_threshold:
                    relationship = EntityRelationship(
                        source_id=entity1_id,
                        target_id=entity2_id,
                        relation_type=RelationType.CO_OCCURS,
                        confidence=min(1.0, self.entity_co_occurrences[pair] / 10.0),  # Scale confidence
                        evidence_text=f"Co-occurred {self.entity_co_occurrences[pair]} times",
                        source_chunk_id=chunk_id,
                        discovery_method="co_occurrence"
                    )
                    
                    self._add_relationship_to_graph(relationship)
                    relationships.append(relationship)
        
        return relationships
    
    def _discover_location_relationships(self, 
                                       entities_by_type: Dict[str, List[StoredEntity]],
                                       chunks: Dict[str, StoredChunk]) -> List[EntityRelationship]:
        """Discover LOCATED_IN relationships between entities and places"""
        relationships = []
        
        places = entities_by_type.get('MIEJSCE', [])
        other_entities = []
        
        # Collect non-place entities
        for entity_type, entities in entities_by_type.items():
            if entity_type != 'MIEJSCE':
                other_entities.extend(entities)
        
        # Look for location patterns in text
        location_patterns = [
            r'\b(?:w|we|na)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)',  # "w Warszawie", "na placu"
            r'\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\s+(?:znajduje|leży|jest)',  # "Warszawa znajduje się"
        ]
        
        for place in places:
            for entity in other_entities:
                # Check if entities share chunk context
                shared_chunks = set(place.source_chunk_ids) & set(entity.source_chunk_ids)
                
                for chunk_id in shared_chunks:
                    if chunk_id in chunks:
                        chunk_text = chunks[chunk_id].text
                        
                        # Look for location patterns
                        for pattern in location_patterns:
                            if re.search(pattern, chunk_text, re.IGNORECASE):
                                relationship = EntityRelationship(
                                    source_id=entity.id,
                                    target_id=place.id,
                                    relation_type=RelationType.LOCATED_IN,
                                    confidence=0.7,
                                    evidence_text=chunk_text[:100],
                                    source_chunk_id=chunk_id,
                                    discovery_method="location_pattern"
                                )
                                
                                self._add_relationship_to_graph(relationship)
                                relationships.append(relationship)
                                break
        
        return relationships
    
    def _discover_authorship_relationships(self,
                                         entities_by_type: Dict[str, List[StoredEntity]],
                                         chunks: Dict[str, StoredChunk]) -> List[EntityRelationship]:
        """Discover AUTHORED_BY relationships"""
        relationships = []
        
        authors = entities_by_type.get('OSOBA', [])
        works = entities_by_type.get('PRZEDMIOT', []) + entities_by_type.get('KONCEPCJA', [])
        
        authorship_patterns = [
            r'\b(?:autor|napisał|stworzył|opracował)\b',
            r'\b(?:dzieło|książka|artykuł|tekst)\b.*\b(?:autor|napisał)\b',
        ]
        
        for author in authors:
            for work in works:
                shared_chunks = set(author.source_chunk_ids) & set(work.source_chunk_ids)
                
                for chunk_id in shared_chunks:
                    if chunk_id in chunks:
                        chunk_text = chunks[chunk_id].text
                        
                        for pattern in authorship_patterns:
                            if re.search(pattern, chunk_text, re.IGNORECASE):
                                relationship = EntityRelationship(
                                    source_id=work.id,
                                    target_id=author.id,
                                    relation_type=RelationType.AUTHORED_BY,
                                    confidence=0.6,
                                    evidence_text=chunk_text[:100],
                                    source_chunk_id=chunk_id,
                                    discovery_method="authorship_pattern"
                                )
                                
                                self._add_relationship_to_graph(relationship)
                                relationships.append(relationship)
                                break
        
        return relationships
    
    def _discover_character_relationships(self,
                                        entities_by_type: Dict[str, List[StoredEntity]],
                                        chunks: Dict[str, StoredChunk]) -> List[EntityRelationship]:
        """Discover character interaction relationships"""
        relationships = []
        
        people = entities_by_type.get('OSOBA', [])
        
        interaction_patterns = [
            r'\b(?:rozmawia|mówi|odpowiada|pyta)\b',
            r'\b(?:spotkał|poznał|widział)\b',
            r'\b(?:dialog|rozmowa|konwersacja)\b',
        ]
        
        for i, person1 in enumerate(people):
            for person2 in people[i+1:]:
                shared_chunks = set(person1.source_chunk_ids) & set(person2.source_chunk_ids)
                
                for chunk_id in shared_chunks:
                    if chunk_id in chunks:
                        chunk_text = chunks[chunk_id].text
                        
                        for pattern in interaction_patterns:
                            if re.search(pattern, chunk_text, re.IGNORECASE):
                                # Create bidirectional interaction relationship
                                relationship = EntityRelationship(
                                    source_id=person1.id,
                                    target_id=person2.id,
                                    relation_type=RelationType.MENTIONED_WITH,
                                    confidence=0.5,
                                    evidence_text=chunk_text[:100],
                                    source_chunk_id=chunk_id,
                                    discovery_method="character_interaction"
                                )
                                
                                self._add_relationship_to_graph(relationship)
                                relationships.append(relationship)
                                break
        
        return relationships
    
    def _add_relationship_to_graph(self, relationship: EntityRelationship):
        """Add relationship to NetworkX graph"""
        self.graph.add_edge(
            relationship.source_id,
            relationship.target_id,
            key=relationship.get_relationship_key(),
            **relationship.to_dict()
        )
    
    def export_graph_data(self) -> Dict[str, Any]:
        """
        Export graph data for visualization and analysis
        
        Returns:
            Dictionary with nodes and edges data
        """
        nodes = []
        edges = []
        
        # Export nodes
        for node_id, node_data in self.graph.nodes(data=True):
            nodes.append({
                'id': node_id,
                'type': node_data.get('type', 'unknown'),
                **node_data.get('data', {})
            })
        
        # Export edges
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
        relationship_counts = Counter()
        
        for _, _, edge_data in self.graph.edges(data=True):
            rel_type = edge_data.get('relation_type', 'unknown')
            relationship_counts[rel_type] += 1
        
        return {
            'total_relationships': self.graph.number_of_edges(),
            'relationship_types': dict(relationship_counts),
            'co_occurrence_pairs': len(self.entity_co_occurrences),
            'chunks_with_entities': len(self.chunk_entity_map)
        }