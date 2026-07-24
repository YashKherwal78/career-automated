import json
import os
from typing import List, Dict, Tuple, Any

from src.discovery.jie.extractors.base import BaseExtractor
from src.discovery.jie.trie_matcher import TrieMatcher

class TechnologyExtractor(BaseExtractor):
    def __init__(self, resource_dir: str = None):
        if not resource_dir:
            resource_dir = os.path.join(os.path.dirname(__file__), "..", "resources")
            
        self.matcher = TrieMatcher()
        self.tech_data = []
        
        techs_path = os.path.join(resource_dir, "technologies.json")
        try:
            with open(techs_path, "r") as f:
                self.tech_data = json.load(f)
                for entry in self.tech_data:
                    canonical = entry.get("canonical")
                    category = entry.get("category")
                    aliases = entry.get("aliases", [])
                    for alias in aliases:
                        # Map alias to tuple containing canonical name and its category
                        self.matcher.add_keyword(alias, (canonical, category))
        except Exception:
            pass

    def extract(self, text: str, **kwargs) -> List[str]:
        """Scans the text using TrieMatcher in a single pass to find all matching technologies."""
        matches = self.matcher.search_all(text)
        
        unique_techs = set()
        for (_, _, (canonical, _)) in matches:
            unique_techs.add(canonical)
            
        return sorted(list(unique_techs))

    def extract_with_categories(self, text: str) -> List[Dict[str, str]]:
        """Extracts technologies alongside their categories for richer dashboard filters."""
        matches = self.matcher.search_all(text)
        
        seen = set()
        results = []
        for (_, _, (canonical, category)) in matches:
            if canonical not in seen:
                seen.add(canonical)
                results.append({
                    "name": canonical,
                    "category": category
                })
        return results
