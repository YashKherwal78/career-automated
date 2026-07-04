from abc import ABC, abstractmethod
from typing import List, Dict, Any

class GraphBackend(ABC):
    """
    Abstract Graph Backend Interface.
    Allows swapping between Graphiti, Neo4j, or other graph databases 
    without changing the Antigravity core architecture.
    """

    @abstractmethod
    def query(self, cypher_or_query: str) -> Any:
        """Executes a raw graph query (e.g., Cypher or custom DSL)."""
        pass

    @abstractmethod
    def get_neighbors(self, node_id: str, depth: int = 1) -> List[Dict[str, Any]]:
        """Returns all dependent or adjacent nodes up to a specific depth."""
        pass

    @abstractmethod
    def get_references(self, symbol: str) -> List[Dict[str, Any]]:
        """Finds all incoming edges (references) to a specific symbol or file."""
        pass
        
    @abstractmethod
    def get_architecture_diff(self, base_commit: str, target_commit: str) -> Dict[str, Any]:
        """Returns a structural diff of the architecture between two points in time."""
        pass
