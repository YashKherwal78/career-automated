import json
import os
from typing import Optional
from src.career_intelligence.models.ontology import OntologyNode, OntologyRelationship
from src.career_intelligence.ontology.interfaces import GraphBackend

class OntologyLoader:
    def __init__(self, backend: GraphBackend):
        self.backend = backend

    def load_from_json(self, json_path: str) -> None:
        """Loads ontology nodes and relationship records from JSON configuration files."""
        if not os.path.exists(json_path):
            return
            
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
                
            for node_data in data.get("nodes", []):
                self.backend.add_node(OntologyNode(**node_data))
                
            for rel_data in data.get("relationships", []):
                self.backend.add_edge(OntologyRelationship(**rel_data))
        except Exception:
            pass

    def load_default_fixtures(self) -> None:
        """Loads core bootstrap technology and framework mapping nodes."""
        # Nodes
        nodes = [
            OntologyNode(id="javascript", canonical_name="JavaScript", aliases=["js"]),
            OntologyNode(id="react", canonical_name="React", aliases=["reactjs"]),
            OntologyNode(id="next.js", canonical_name="Next.js", aliases=["nextjs"]),
            OntologyNode(id="python", canonical_name="Python", aliases=["py"]),
            OntologyNode(id="fastapi", canonical_name="FastAPI"),
            OntologyNode(id="docker", canonical_name="Docker"),
            OntologyNode(id="kubernetes", canonical_name="Kubernetes", aliases=["k8s"])
        ]
        for n in nodes:
            self.backend.add_node(n)
            
        # Relationships
        rels = [
            OntologyRelationship(source_id="next.js", target_id="react", relationship_type="IS_A"),
            OntologyRelationship(source_id="react", target_id="javascript", relationship_type="IS_A"),
            OntologyRelationship(source_id="fastapi", target_id="python", relationship_type="IS_A"),
            OntologyRelationship(source_id="kubernetes", target_id="docker", relationship_type="REQUIRES"),
            OntologyRelationship(source_id="docker", target_id="kubernetes", relationship_type="PREREQUISITE")
        ]
        for r in rels:
            self.backend.add_edge(r)
