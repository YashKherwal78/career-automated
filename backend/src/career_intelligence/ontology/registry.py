from typing import Dict, List, Set, Tuple, Any
from src.career_intelligence.ontology.models import OntologyNode, OntologyRelationship

class CareerOntologyRegistry:
    def __init__(self):
        self.nodes: Dict[str, OntologyNode] = {}
        # Adjacency maps for source_id -> list of (target_id, relation_type)
        self.outgoing: Dict[str, List[Tuple[str, str]]] = {}
        self.incoming: Dict[str, List[Tuple[str, str]]] = {}

        # Self-populate standard core relationship foundations as defaults
        self._initialize_core_foundations()

    def add_node(self, node: OntologyNode):
        self.nodes[node.id] = node
        if node.id not in self.outgoing:
            self.outgoing[node.id] = []
        if node.id not in self.incoming:
            self.incoming[node.id] = []

    def add_relationship(self, rel: OntologyRelationship):
        if rel.source_id not in self.outgoing:
            self.outgoing[rel.source_id] = []
        if rel.target_id not in self.incoming:
            self.incoming[rel.target_id] = []
            
        self.outgoing[rel.source_id].append((rel.target_id, rel.relation_type))
        self.incoming[rel.target_id].append((rel.source_id, rel.relation_type))

    def check_similarity(self, source: str, target: str) -> float:
        """Computes similarity coefficient between two ontology nodes using path distance heuristics."""
        s_clean = source.lower().strip()
        t_clean = target.lower().strip()
        
        if s_clean == t_clean:
            return 1.0
            
        # Hardcoded traversal path placeholders for core concepts (e.g. Next.js -> React -> JavaScript)
        relations = {
            ("next.js", "react"): 0.9,
            ("react", "javascript"): 0.8,
            ("fastapi", "python"): 0.8,
            ("docker", "kubernetes"): 0.7,
            ("django", "python"): 0.8,
            ("postgres", "sql"): 0.8,
            ("postgresql", "postgres"): 1.0
        }
        
        # Check explicit mappings
        if (s_clean, t_clean) in relations:
            return relations[(s_clean, t_clean)]
        if (t_clean, s_clean) in relations:
            return relations[(t_clean, s_clean)]
            
        return 0.0

    def _initialize_core_foundations(self):
        # Prepopulate basic node maps for common packages
        core_nodes = [
            OntologyNode(id="javascript", name="JavaScript", type="technology"),
            OntologyNode(id="react", name="React", type="technology"),
            OntologyNode(id="next.js", name="Next.js", type="technology"),
            OntologyNode(id="python", name="Python", type="technology"),
            OntologyNode(id="fastapi", name="FastAPI", type="technology"),
            OntologyNode(id="docker", name="Docker", type="technology"),
            OntologyNode(id="kubernetes", name="Kubernetes", type="technology")
        ]
        for node in core_nodes:
            self.add_node(node)
            
        core_relations = [
            OntologyRelationship(source_id="react", target_id="javascript", relation_type="is_a"),
            OntologyRelationship(source_id="next.js", target_id="react", relation_type="requires"),
            OntologyRelationship(source_id="fastapi", target_id="python", relation_type="is_a"),
            OntologyRelationship(source_id="kubernetes", target_id="docker", relation_type="requires")
        ]
        for rel in core_relations:
            self.add_relationship(rel)
