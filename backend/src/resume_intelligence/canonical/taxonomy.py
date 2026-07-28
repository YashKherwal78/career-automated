"""
Skill Taxonomy and DAG Ontology Subsystem.

Provides hierarchical skill modeling (e.g., Backend -> Python -> FastAPI)
enabling exact and semantic skill reasoning, parent/child traversal,
and canonical skill mapping.
"""

from typing import Dict, List, Set, Optional
from pydantic import BaseModel, Field


class TaxonomyNode(BaseModel):
    name: str
    category: str
    parents: List[str] = Field(default_factory=list)
    children: List[str] = Field(default_factory=list)
    synonyms: List[str] = Field(default_factory=list)


class SkillTaxonomy:
    """Pre-populated skill taxonomy hierarchy."""
    
    def __init__(self):
        self.nodes: Dict[str, TaxonomyNode] = {}
        self.synonym_map: Dict[str, str] = {}
        self._build_default_taxonomy()

    def _build_default_taxonomy(self):
        default_tree = [
            # Category Root Nodes
            ("AI/ML", "Category", [], ["LangGraph", "LangChain", "Groq/LLaMA", "MCP", "Hybrid RAG", "Multi-Agent Systems", "PyTorch", "TensorFlow", "Scikit-learn", "BGE-M3", "AstraDB", "Prompt Engineering"]),
            ("Backend & Infra", "Category", [], ["Python", "FastAPI", "Docker", "AWS EC2", "Playwright", "IMAP/SMTP", "Stream Processing", "REST APIs", "SQL", "SQLite", "PostgreSQL", "Redis"]),
            ("Product", "Category", [], ["PRD Writing", "MVP Scoping", "Customer Discovery", "Roadmapping", "Prioritisation (RICE, Knapsack)", "A/B Testing", "Funnel Analysis", "Metrics Definition"]),
            ("Data & Analytics", "Category", [], ["SQL", "Pandas", "NumPy", "Cohort Queries", "Data Pipelines", "A/B Testing", "Multi-Objective Optimisation"]),
            
            # Specific Tech Nodes
            ("Python", "Language", ["Backend & Infra"], ["FastAPI", "Pandas", "NumPy", "Scikit-learn", "TensorFlow", "PyTorch", "Playwright"]),
            ("FastAPI", "Framework", ["Python", "Backend & Infra"], []),
            ("LangGraph", "Framework", ["AI/ML"], ["Multi-Agent Systems"]),
            ("LangChain", "Framework", ["AI/ML"], []),
            ("Docker", "DevOps", ["Backend & Infra"], []),
            ("AWS EC2", "Cloud", ["Backend & Infra"], []),
            ("SQL", "Database", ["Backend & Infra", "Data & Analytics"], ["SQLite", "PostgreSQL"]),
            ("SQLite", "Database", ["SQL"], []),
            ("React Native", "Mobile", ["Frontend"], []),
        ]
        
        for name, category, parents, children in default_tree:
            node = TaxonomyNode(name=name, category=category, parents=parents, children=children)
            self.nodes[name.lower()] = node
            
        # Synonyms
        syns = {
            "fast api": "FastAPI",
            "langchain": "LangChain",
            "lang graph": "LangGraph",
            "postgres": "PostgreSQL",
            "postgresql": "PostgreSQL",
            "aws": "AWS EC2",
            "ec2": "AWS EC2",
            "reactnative": "React Native",
            "scikit learn": "Scikit-learn",
            "sklearn": "Scikit-learn",
            "tensorflow": "TensorFlow",
            "tf": "TensorFlow",
            "bge m3": "BGE-M3",
            "astradb": "AstraDB",
        }
        for syn, canonical in syns.items():
            self.synonym_map[syn.lower()] = canonical

    def canonicalize(self, skill_name: str) -> str:
        """Resolves raw skill string to canonical form."""
        s_clean = skill_name.strip()
        s_lower = s_clean.lower()
        if s_lower in self.synonym_map:
            return self.synonym_map[s_lower]
        if s_lower in self.nodes:
            return self.nodes[s_lower].name
        return s_clean

    def get_related_skills(self, skill_name: str) -> List[str]:
        """Returns parents, children, and siblings of a skill."""
        canonical = self.canonicalize(skill_name)
        c_lower = canonical.lower()
        if c_lower not in self.nodes:
            return []
        node = self.nodes[c_lower]
        related = set(node.parents + node.children)
        return list(related)
