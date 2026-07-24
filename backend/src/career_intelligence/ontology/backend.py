from typing import List, Dict, Any, Optional, Set
from src.career_intelligence.models.ontology import OntologyNode, OntologyRelationship
from src.career_intelligence.ontology.interfaces import GraphBackend

class MemoryGraphBackend(GraphBackend):
    def __init__(self):
        self.nodes: Dict[str, OntologyNode] = {}
        self.adjacency: Dict[str, List[OntologyRelationship]] = {}

    def add_node(self, node: OntologyNode) -> None:
        node_id_lower = node.id.lower().strip()
        self.nodes[node_id_lower] = node
        if node_id_lower not in self.adjacency:
            self.adjacency[node_id_lower] = []

    def get_node(self, node_id: str) -> Optional[OntologyNode]:
        return self.nodes.get(node_id.lower().strip())

    def add_edge(self, edge: OntologyRelationship) -> None:
        source_lower = edge.source_id.lower().strip()
        target_lower = edge.target_id.lower().strip()
        
        # Ensure nodes exist
        if source_lower not in self.nodes:
            self.add_node(OntologyNode(id=edge.source_id, canonical_name=edge.source_id.title()))
        if target_lower not in self.nodes:
            self.add_node(OntologyNode(id=edge.target_id, canonical_name=edge.target_id.title()))
            
        self.adjacency[source_lower].append(edge)

    def get_neighbors(self, node_id: str, edge_type: Optional[str] = None) -> List[str]:
        node_id_lower = node_id.lower().strip()
        if node_id_lower not in self.adjacency:
            return []
            
        neighbors = []
        for edge in self.adjacency[node_id_lower]:
            if edge_type is None or edge.relationship_type.upper() == edge_type.upper():
                neighbors.append(edge.target_id.lower().strip())
        return neighbors

    def get_nodes(self) -> List[OntologyNode]:
        return list(self.nodes.values())

    def get_relationships(self) -> List[OntologyRelationship]:
        all_rels = []
        for rels in self.adjacency.values():
            all_rels.extend(rels)
        return all_rels
