from typing import List, Dict, Set
from src.career_intelligence.learning.models import LearningNode

class LearningGraphEngine:
    def __init__(self):
        self.nodes: Dict[str, LearningNode] = {}
        self._initialize_learning_dependencies()

    def add_learning_node(self, node: LearningNode) -> None:
        self.nodes[node.id] = node

    def get_recommended_learning_order(self, missing_techs: List[str]) -> List[str]:
        """Resolves missing technologies into a logical prerequisite learning sequence using learning dependencies."""
        missing_set = {t.lower().strip() for t in missing_techs}
        order = []
        visited = set()

        def dfs(node_id: str):
            if node_id in visited:
                return
            visited.add(node_id)
            
            # Recurse prerequisites first
            node = self.nodes.get(node_id)
            if node:
                for prereq in node.prerequisites:
                    if prereq in missing_set:
                        dfs(prereq)
            
            # Map back to canonical display
            node_obj = self.nodes.get(node_id)
            name = node_obj.name if node_obj else node_id.title()
            if name not in order:
                order.append(name)

        # Execute DFS on each missing element
        for tech in missing_techs:
            tech_clean = tech.lower().strip()
            if tech_clean in self.nodes:
                dfs(tech_clean)
            else:
                if tech not in order:
                    order.append(tech)

        return order

    def _initialize_learning_dependencies(self):
        # Prepopulate dependency chains for common DevOps and stack paradigms
        deps = [
            LearningNode(id="kubernetes", name="Kubernetes", prerequisites=["docker"]),
            LearningNode(id="docker", name="Docker", prerequisites=["linux"]),
            LearningNode(id="linux", name="Linux", prerequisites=[]),
            LearningNode(id="next.js", name="Next.js", prerequisites=["react"]),
            LearningNode(id="react", name="React", prerequisites=["javascript"]),
            LearningNode(id="javascript", name="JavaScript", prerequisites=[]),
            LearningNode(id="fastapi", name="FastAPI", prerequisites=["python"]),
            LearningNode(id="python", name="Python", prerequisites=[])
        ]
        for d in deps:
            self.add_learning_node(d)
