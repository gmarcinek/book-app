"""
Union-Find data structure for entity clustering and deduplication
Simple and efficient implementation for managing entity merges
"""

from typing import Dict, Set, List, Optional


class EntityUnionFind:
    """
    Union-Find structure for clustering similar entities
    
    Maintains canonical entity for each cluster and tracks all members
    """
    
    def __init__(self):
        self.parent: Dict[str, str] = {}  # entity_id -> canonical_entity_id
        self.rank: Dict[str, int] = {}    # for union optimization
        self.members: Dict[str, Set[str]] = {}  # canonical_id -> all_member_ids
    
    def add_entity(self, entity_id: str) -> str:
        """
        Add new entity to union-find structure
        
        Returns:
            The canonical entity ID (initially itself)
        """
        if entity_id not in self.parent:
            self.parent[entity_id] = entity_id
            self.rank[entity_id] = 0
            self.members[entity_id] = {entity_id}
        
        return entity_id
    
    def find(self, entity_id: str) -> str:
        """
        Find canonical entity for given entity with path compression
        
        Returns:
            Canonical entity ID for this cluster
        """
        if entity_id not in self.parent:
            return self.add_entity(entity_id)
        
        # Path compression optimization
        if self.parent[entity_id] != entity_id:
            self.parent[entity_id] = self.find(self.parent[entity_id])
        
        return self.parent[entity_id]
    
    def union(self, entity1_id: str, entity2_id: str) -> str:
        """
        Merge two entities into same cluster
        
        Returns:
            Canonical entity ID for the merged cluster
        """
        root1 = self.find(entity1_id)
        root2 = self.find(entity2_id)
        
        if root1 == root2:
            return root1  # Already in same cluster
        
        # Union by rank optimization
        if self.rank[root1] < self.rank[root2]:
            root1, root2 = root2, root1
        
        # Make root1 the canonical entity
        self.parent[root2] = root1
        
        # Merge member sets
        self.members[root1].update(self.members[root2])
        del self.members[root2]
        
        # Update rank if needed
        if self.rank[root1] == self.rank[root2]:
            self.rank[root1] += 1
        
        return root1
    
    def get_cluster_members(self, entity_id: str) -> Set[str]:
        """Get all entities in the same cluster"""
        canonical = self.find(entity_id)
        return self.members.get(canonical, {entity_id}).copy()
    
    def get_all_clusters(self) -> Dict[str, Set[str]]:
        """Get all clusters with their members"""
        return {canonical: members.copy() for canonical, members in self.members.items()}
    
    def is_connected(self, entity1_id: str, entity2_id: str) -> bool:
        """Check if two entities are in the same cluster"""
        return self.find(entity1_id) == self.find(entity2_id)
    
    def get_cluster_count(self) -> int:
        """Get total number of clusters"""
        return len(self.members)
    
    def get_cluster_size(self, entity_id: str) -> int:
        """Get size of cluster containing given entity"""
        canonical = self.find(entity_id)
        return len(self.members.get(canonical, {entity_id}))