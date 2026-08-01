"""
Semantic Reasoning Models — Phase 2 Semantic Reasoning Layer

Defines CapabilityNode, SemanticAdjacency, and OntologyGraph.

Invariant: Semantic reasoning models contain ZERO scoring logic.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CapabilityNode(BaseModel):
    """A node in the capability ontology graph."""
    id: str
    canonical_name: str
    category: str = "skill"  # "language", "framework", "database", "cloud", "tool", "concept"
    aliases: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)  # list of prerequisite capability IDs
    difficulty_level: int = 1  # 1 (beginner) to 5 (expert)

    class Config:
        frozen = True


class SemanticAdjacency(BaseModel):
    """Describes an adjacency or relationship between two capabilities."""
    source_capability: str
    target_capability: str
    relationship_type: str  # "EQUIVALENT_TO", "REQUIRES", "PREREQUISITE_OF", "RELATED_TO", "PARENT_OF"
    weight: float = 1.0
    similarity_score: float = 0.8

    class Config:
        frozen = True


class OntologyGraph(BaseModel):
    """Graph structure containing ontology nodes and relationship edges."""
    nodes: Dict[str, CapabilityNode] = Field(default_factory=dict)
    relationships: List[SemanticAdjacency] = Field(default_factory=list)

    class Config:
        frozen = True
