from typing import List, Dict, Any, Optional, Set
from collections import deque
from src.career_intelligence.ontology.interfaces import GraphBackend, GraphService

class CareerGraphService(GraphService):
    def __init__(self, backend: GraphBackend):
        self.backend = backend

    def check_similarity(self, node_a: str, node_b: str) -> float:
        """Calculates similarity score (0.0 to 1.0) between node_a and node_b."""
        id_a = node_a.lower().strip()
        id_b = node_b.lower().strip()
        
        if id_a == id_b:
            return 1.0

        # Check aliases of both nodes
        node_obj_a = self.backend.get_node(id_a)
        node_obj_b = self.backend.get_node(id_b)
        
        if node_obj_a and id_b in [alias.lower().strip() for alias in node_obj_a.aliases]:
            return 1.0
        if node_obj_b and id_a in [alias.lower().strip() for alias in node_obj_b.aliases]:
            return 1.0

        # BFS shortest path traversal to find topological distance
        path = self.get_shortest_path(id_a, id_b)
        if path:
            distance = len(path) - 1
            # Return score decayed by path length
            return max(0.0, 1.0 - (0.1 * distance))
            
        # Try reverse path
        rev_path = self.get_shortest_path(id_b, id_a)
        if rev_path:
            distance = len(rev_path) - 1
            return max(0.0, 1.0 - (0.15 * distance))

        # Check common siblings
        ancestors_a = self.get_ancestors(id_a)
        ancestors_b = self.get_ancestors(id_b)
        if ancestors_a.intersection(ancestors_b):
            return 0.7

        return 0.0

    def get_shortest_path(self, start_node: str, end_node: str) -> List[str]:
        """Finds the shortest path using Breadth-First Search."""
        start = start_node.lower().strip()
        end = end_node.lower().strip()
        
        if not self.backend.get_node(start) or not self.backend.get_node(end):
            return []
            
        queue = deque([[start]])
        visited = {start}
        
        while queue:
            path = queue.popleft()
            node = path[-1]
            if node == end:
                return path
                
            for neighbor in self.backend.get_neighbors(node):
                if neighbor not in visited:
                    visited.add(neighbor)
                    new_path = list(path)
                    new_path.append(neighbor)
                    queue.append(new_path)
        return []

    def get_prerequisites(self, node_id: str) -> List[str]:
        """Looks up prerequisite relationships from the graph backend."""
        # Find adjacent nodes with 'PREREQUISITE' edge relationship type
        return self.backend.get_neighbors(node_id, edge_type="PREREQUISITE")

    def get_ancestors(self, node_id: str) -> Set[str]:
        """Recursively resolves parent nodes via IS_A or PART_OF edge types."""
        visited = set()
        stack = [node_id.lower().strip()]
        
        while stack:
            curr = stack.pop()
            if curr not in visited:
                if curr != node_id.lower().strip():
                    visited.add(curr)
                # Find parents
                for rel in self.backend.get_relationships():
                    if rel.source_id.lower().strip() == curr and rel.relationship_type.upper() in ["IS_A", "PART_OF"]:
                        stack.append(rel.target_id.lower().strip())
        return visited

    def get_descendants(self, node_id: str) -> Set[str]:
        """Recursively resolves children nodes (inverse of IS_A or PART_OF)."""
        visited = set()
        stack = [node_id.lower().strip()]
        
        while stack:
            curr = stack.pop()
            if curr not in visited:
                if curr != node_id.lower().strip():
                    visited.add(curr)
                # Find children (where target == curr)
                for rel in self.backend.get_relationships():
                    if rel.target_id.lower().strip() == curr and rel.relationship_type.upper() in ["IS_A", "PART_OF"]:
                        stack.append(rel.source_id.lower().strip())
        return visited
