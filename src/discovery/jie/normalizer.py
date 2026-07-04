import yaml
import os
from src.discovery.jie.models import StructuredJob

class Normalizer:
    def __init__(self, skills_config_path: str = None):
        if not skills_config_path:
            skills_config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'skills.yaml')
            
        self.skill_map = {}
        try:
            with open(skills_config_path, 'r') as f:
                skills_data = yaml.safe_load(f)
                if skills_data:
                    for canonical, data in skills_data.items():
                        aliases = data.get('aliases', [])
                        for alias in aliases:
                            self.skill_map[alias.lower()] = canonical
        except Exception as e:
            print(f"Warning: Failed to load skills config: {e}")

    def _normalize_skill(self, raw_skill: str) -> str:
        return self.skill_map.get(raw_skill.lower(), raw_skill.title())

    def normalize(self, job: StructuredJob) -> StructuredJob:
        for req in job.requirements:
            if req.type == "skill":
                req.name = self._normalize_skill(req.name)
        return job
