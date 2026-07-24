import json
import os
from src.career_intelligence.ontology.models import OntologyNode, OntologyRelationship
from src.career_intelligence.ontology.registry import CareerOntologyRegistry

class OntologyLoader:
    @staticmethod
    def load_from_json(json_path: str, registry: CareerOntologyRegistry) -> None:
        """Loads ontology nodes and relationships from a JSON config file."""
        if not os.path.exists(json_path):
            return
            
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
                
            # Parse nodes
            for node_data in data.get("nodes", []):
                node = OntologyNode(**node_data)
                registry.add_node(node)
                
            # Parse relationships
            for rel_data in data.get("relationships", []):
                rel = OntologyRelationship(**rel_data)
                registry.add_relationship(rel)
        except Exception:
            pass
