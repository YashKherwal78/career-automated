import json
import os
from typing import List

from src.discovery.jie.extractors.base import BaseExtractor
from src.discovery.jie.trie_matcher import TrieMatcher

class SkillExtractor(BaseExtractor):
    def __init__(self, resource_dir: str = None):
        if not resource_dir:
            resource_dir = os.path.join(os.path.dirname(__file__), "..", "resources")
            
        self.matcher = TrieMatcher()
        skills_path = os.path.join(resource_dir, "skills.json")
        try:
            with open(skills_path, "r") as f:
                skills_data = json.load(f)
                for canonical, aliases in skills_data.items():
                    for alias in aliases:
                        self.matcher.add_keyword(alias, canonical)
        except Exception:
            pass

    def extract(self, text: str, **kwargs) -> List[str]:
        """Extracts and normalizes skills in O(N) single pass using TrieMatcher."""
        matches = self.matcher.search_all(text)
        
        unique_skills = set()
        for (_, _, canonical) in matches:
            unique_skills.add(canonical)
            
        return sorted(list(unique_skills))
