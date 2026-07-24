from typing import List, Dict, Any, Optional, Set, Protocol
from src.career_intelligence.models.ontology import OntologyNode, OntologyRelationship

class GraphBackend(Protocol):
    def add_node(self, node: OntologyNode) -> None:
        """Adds a node to the graph storage."""
        ...

    def get_node(self, node_id: str) -> Optional[OntologyNode]:
        """Retrieves a node by identifier."""
        ...

    def add_edge(self, edge: OntologyRelationship) -> None:
        """Adds a directed, typed edge between nodes."""
        ...

    def get_neighbors(self, node_id: str, edge_type: Optional[str] = None) -> List[str]:
        """Returns adjacent node identifiers, optionally filtered by relationship type."""
        ...

    def get_nodes(self) -> List[OntologyNode]:
        """Returns all nodes in the graph."""
        ...

    def get_relationships(self) -> List[OntologyRelationship]:
        """Returns all relationships in the graph."""
        ...

class GraphService(Protocol):
    def check_similarity(self, node_a: str, node_b: str) -> float:
        """Calculates similarity score (0.0 to 1.0) between two nodes."""
        ...

    def get_shortest_path(self, start_node: str, end_node: str) -> List[str]:
        """Finds the shortest path of identifiers between two nodes."""
        ...

    def get_prerequisites(self, node_id: str) -> List[str]:
        """Finds prerequisite nodes required by this node."""
        ...

    def get_ancestors(self, node_id: str) -> Set[str]:
        """Finds all parent/ancestor identifiers."""
        ...

    def get_descendants(self, node_id: str) -> Set[str]:
        """Finds all child/descendant identifiers."""
        ...
