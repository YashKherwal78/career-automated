"""
SemanticReasoner — Phase 2 Semantic Reasoning Layer

Performs graph traversal, capability adjacency, skill equivalence, and prerequisite
discovery over a localized ontology graph.

Responsibilities:
  - Traversal of capability relationships.
  - Identification of skill equivalences and aliases.
  - Prerequisite discovery for missing job capabilities.
  - Domain similarity resolution.
  - Zero scoring logic.

Invariant: No score calculations. Pure graph/semantic reasoning.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Set, Tuple

from src.career_intelligence.reasoning.models import (
    CapabilityNode,
    OntologyGraph,
    SemanticAdjacency,
)

logger = logging.getLogger("SemanticReasoner")


# ---------------------------------------------------------------------------
# Default In-Memory Ontology Knowledge Graph
# ---------------------------------------------------------------------------

_DEFAULT_NODES: Dict[str, CapabilityNode] = {
    "python": CapabilityNode(id="python", canonical_name="Python", category="language", aliases=["py", "python3"]),
    "javascript": CapabilityNode(id="javascript", canonical_name="JavaScript", category="language", aliases=["js", "es6"]),
    "typescript": CapabilityNode(id="typescript", canonical_name="TypeScript", category="language", aliases=["ts"], prerequisites=["javascript"]),
    "react": CapabilityNode(id="react", canonical_name="React", category="framework", aliases=["react.js", "reactjs"], prerequisites=["javascript"]),
    "fastapi": CapabilityNode(id="fastapi", canonical_name="FastAPI", category="framework", aliases=["fast api"], prerequisites=["python"]),
    "django": CapabilityNode(id="django", canonical_name="Django", category="framework", aliases=[], prerequisites=["python"]),
    "docker": CapabilityNode(id="docker", canonical_name="Docker", category="tool", aliases=["containerization"]),
    "kubernetes": CapabilityNode(id="kubernetes", canonical_name="Kubernetes", category="tool", aliases=["k8s"], prerequisites=["docker"]),
    "postgres": CapabilityNode(id="postgres", canonical_name="PostgreSQL", category="database", aliases=["postgresql", "postgres"]),
    "redis": CapabilityNode(id="redis", canonical_name="Redis", category="database", aliases=[]),
    "pytorch": CapabilityNode(id="pytorch", canonical_name="PyTorch", category="framework", aliases=["torch"], prerequisites=["python"]),
    "tensorflow": CapabilityNode(id="tensorflow", canonical_name="TensorFlow", category="framework", aliases=["tf"], prerequisites=["python"]),
}

_DEFAULT_RELATIONSHIPS: List[SemanticAdjacency] = [
    # Skill equivalences
    SemanticAdjacency(source_capability="postgres", target_capability="postgresql", relationship_type="EQUIVALENT_TO", similarity_score=1.0),
    SemanticAdjacency(source_capability="react", target_capability="reactjs", relationship_type="EQUIVALENT_TO", similarity_score=1.0),
    SemanticAdjacency(source_capability="fastapi", target_capability="flask", relationship_type="RELATED_TO", similarity_score=0.8),
    SemanticAdjacency(source_capability="pytorch", target_capability="tensorflow", relationship_type="RELATED_TO", similarity_score=0.75),
    # Prerequisites
    SemanticAdjacency(source_capability="typescript", target_capability="javascript", relationship_type="REQUIRES", similarity_score=0.9),
    SemanticAdjacency(source_capability="react", target_capability="javascript", relationship_type="REQUIRES", similarity_score=0.9),
    SemanticAdjacency(source_capability="fastapi", target_capability="python", relationship_type="REQUIRES", similarity_score=0.9),
    SemanticAdjacency(source_capability="kubernetes", target_capability="docker", relationship_type="REQUIRES", similarity_score=0.9),
    SemanticAdjacency(source_capability="pytorch", target_capability="python", relationship_type="REQUIRES", similarity_score=0.9),
]


class SemanticReasoner:
    """Provides semantic graph operations, capability adjacency, and prerequisite discovery."""

    def __init__(self, graph: OntologyGraph | None = None) -> None:
        if graph is None:
            self._graph = OntologyGraph(
                nodes=_DEFAULT_NODES,
                relationships=_DEFAULT_RELATIONSHIPS,
            )
        else:
            self._graph = graph

    def resolve_aliases(self, capability: str) -> str:
        """Resolve a raw capability name or alias to its canonical name."""
        cap_lower = capability.strip().lower()

        # Direct node lookup
        if cap_lower in self._graph.nodes:
            return self._graph.nodes[cap_lower].canonical_name

        # Alias lookup
        for node in self._graph.nodes.values():
            if cap_lower in [a.lower() for a in node.aliases]:
                return node.canonical_name

        return capability.strip()

    def is_equivalent(self, cap1: str, cap2: str) -> bool:
        """Check if two capabilities are equivalent or aliases."""
        c1 = self.resolve_aliases(cap1).lower()
        c2 = self.resolve_aliases(cap2).lower()
        if c1 == c2:
            return True

        for rel in self._graph.relationships:
            if rel.relationship_type == "EQUIVALENT_TO":
                src = rel.source_capability.lower()
                tgt = rel.target_capability.lower()
                if (src == c1 and tgt == c2) or (src == c2 and tgt == c1):
                    return True

        return False

    def find_adjacencies(self, capability: str) -> List[SemanticAdjacency]:
        """Find adjacent capabilities in the ontology graph."""
        cap_lower = capability.strip().lower()
        adjacencies: List[SemanticAdjacency] = []

        for rel in self._graph.relationships:
            if rel.source_capability.lower() == cap_lower or rel.target_capability.lower() == cap_lower:
                adjacencies.append(rel)

        return adjacencies

    def discover_prerequisites(self, missing_capability: str) -> List[str]:
        """Discover prerequisite capabilities required before learning a missing capability."""
        cap_key = missing_capability.strip().lower()

        # Check node definition
        if cap_key in self._graph.nodes:
            node = self._graph.nodes[cap_key]
            if node.prerequisites:
                return [self.resolve_aliases(p) for p in node.prerequisites]

        # Check relationships
        prereqs: Set[str] = set()
        for rel in self._graph.relationships:
            if rel.source_capability.lower() == cap_key and rel.relationship_type == "REQUIRES":
                prereqs.add(self.resolve_aliases(rel.target_capability))

        return list(prereqs)

    def compute_domain_similarity(self, domain1: str, domain2: str) -> float:
        """Compute similarity score between two domains (0.0 to 1.0)."""
        d1 = domain1.strip().lower()
        d2 = domain2.strip().lower()

        if d1 == d2:
            return 1.0

        # Predefined domain similarities
        domain_clusters = [
            {"backend", "fullstack", "devops"},
            {"frontend", "fullstack", "mobile"},
            {"data_science", "machine_learning", "data_engineering"},
        ]

        for cluster in domain_clusters:
            if d1 in cluster and d2 in cluster:
                return 0.75

        return 0.2
