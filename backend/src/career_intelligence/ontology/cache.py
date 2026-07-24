from typing import Dict, Any, Optional, List, Set
from src.career_intelligence.ontology.interfaces import GraphService

class CachedGraphService(GraphService):
    def __init__(self, delegate: GraphService):
        self.delegate = delegate
        self._similarity_cache: Dict[str, float] = {}
        self._path_cache: Dict[str, List[str]] = {}

    def check_similarity(self, node_a: str, node_b: str) -> float:
        key = f"{node_a.lower()}||{node_b.lower()}"
        if key not in self._similarity_cache:
            self._similarity_cache[key] = self.delegate.check_similarity(node_a, node_b)
        return self._similarity_cache[key]

    def get_shortest_path(self, start_node: str, end_node: str) -> List[str]:
        key = f"{start_node.lower()}||{end_node.lower()}"
        if key not in self._path_cache:
            self._path_cache[key] = self.delegate.get_shortest_path(start_node, end_node)
        return self._path_cache[key]

    def get_prerequisites(self, node_id: str) -> List[str]:
        return self.delegate.get_prerequisites(node_id)

    def get_ancestors(self, node_id: str) -> Set[str]:
        return self.delegate.get_ancestors(node_id)

    def get_descendants(self, node_id: str) -> Set[str]:
        return self.delegate.get_descendants(node_id)
