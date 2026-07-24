import re
from src.career_intelligence.capability.interfaces import CapabilityNormalizer

class DefaultCapabilityNormalizer(CapabilityNormalizer):
    def __init__(self):
        # Normalization lookup dict for common tech/keywords
        self.aliases = {
            "nodejs": "Node.js",
            "node.js": "Node.js",
            "node js": "Node.js",
            "reactjs": "React",
            "react.js": "React",
            "react js": "React",
            "nextjs": "Next.js",
            "next js": "Next.js",
            "fastapi": "FastAPI",
            "fast api": "FastAPI",
            "py": "Python",
            "python": "Python",
            "js": "JavaScript",
            "javascript": "JavaScript",
            "ts": "TypeScript",
            "typescript": "TypeScript",
            "docker": "Docker",
            "k8s": "Kubernetes",
            "kubernetes": "Kubernetes"
        }

    def normalize(self, name: str) -> str:
        """Normalizes different raw string variations of technology/skills names."""
        if not name:
            return ""
        clean = re.sub(r'\s+', ' ', name.strip().lower())
        return self.aliases.get(clean, name.strip())
