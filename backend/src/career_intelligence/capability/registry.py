from typing import Dict, List
from src.career_intelligence.models.capability import Capability

class CapabilityRegistry:
    def __init__(self):
        # Maps normalized keyword names to list of Capability nodes
        self.mappings: Dict[str, List[Capability]] = {}
        self._initialize_default_mappings()

    def register(self, keyword: str, capabilities: List[Capability]) -> None:
        self.mappings[keyword.lower().strip()] = capabilities

    def lookup(self, keyword: str) -> List[Capability]:
        return self.mappings.get(keyword.lower().strip(), [])

    def _initialize_default_mappings(self):
        # Frontend capabilities
        fe_cap = [
            Capability(id="frontend_dev", name="Frontend Development", domain="frontend"),
            Capability(id="ui_design", name="UI Design", domain="frontend")
        ]
        self.register("react", fe_cap)
        self.register("next.js", fe_cap + [Capability(id="spa", name="Single Page Applications", domain="frontend")])

        # Backend capabilities
        be_cap = [
            Capability(id="backend_dev", name="Backend Development", domain="backend"),
            Capability(id="api_design", name="API Design", domain="backend"),
            Capability(id="microservices", name="Microservices", domain="backend")
        ]
        self.register("fastapi", be_cap)
        self.register("python", [Capability(id="backend_dev", name="Backend Development", domain="backend")])
        self.register("nodejs", be_cap)

        # DevOps capabilities
        devops_cap = [
            Capability(id="devops", name="DevOps", domain="ops"),
            Capability(id="containerization", name="Containerization", domain="ops")
        ]
        self.register("docker", devops_cap)
        self.register("kubernetes", devops_cap + [Capability(id="orchestration", name="Container Orchestration", domain="ops")])
