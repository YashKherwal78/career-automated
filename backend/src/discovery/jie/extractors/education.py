import json
import os
import re
from typing import List

from src.discovery.jie.extractors.base import BaseExtractor
from src.discovery.jie.models import EducationInfo
from src.discovery.jie.trie_matcher import TrieMatcher

class EducationExtractor(BaseExtractor):
    def __init__(self, resource_dir: str = None):
        if not resource_dir:
            resource_dir = os.path.join(os.path.dirname(__file__), "..", "resources")
            
        # Load Degree Alias mapping
        self.degree_matcher = TrieMatcher()
        degrees_path = os.path.join(resource_dir, "degrees.json")
        try:
            with open(degrees_path, "r") as f:
                self.degrees_data = json.load(f)
                for canonical, aliases in self.degrees_data.items():
                    for alias in aliases:
                        self.degree_matcher.add_keyword(alias, canonical)
        except Exception:
            self.degrees_data = {}
            
        # Load Education Fields Alias mapping
        self.fields_matcher = TrieMatcher()
        fields_path = os.path.join(resource_dir, "education_fields.json")
        try:
            with open(fields_path, "r") as f:
                self.fields_data = json.load(f)
                for canonical, aliases in self.fields_data.items():
                    for alias in aliases:
                        self.fields_matcher.add_keyword(alias, canonical)
        except Exception:
            self.fields_data = {}

    def find_degrees(self, text: str) -> List[str]:
        """Finds raw matches of degrees in the text using TrieMatcher."""
        matches = self.degree_matcher.search_all(text)
        return [val for (_, _, val) in matches]

    def find_fields(self, text: str) -> List[str]:
        """Finds raw matches of education fields in the text using TrieMatcher."""
        matches = self.fields_matcher.search_all(text)
        return [val for (_, _, val) in matches]

    def normalize(self, raw_degrees: List[str], raw_fields: List[str]) -> EducationInfo:
        """Normalizes and deduplicates raw matches into canonical EducationInfo Pydantic model."""
        # TrieMatcher already maps aliases to their canonical representation
        unique_degrees = []
        for d in raw_degrees:
            if d not in unique_degrees:
                unique_degrees.append(d)
                
        unique_fields = []
        for f in raw_fields:
            if f not in unique_fields:
                unique_fields.append(f)
                
        return EducationInfo(
            degrees=unique_degrees,
            fields=unique_fields
        )

    def extract(self, text: str, **kwargs) -> EducationInfo:
        """Extracts and normalizes degrees and fields of study from job description text."""
        raw_degrees = self.find_degrees(text)
        raw_fields = self.find_fields(text)
        return self.normalize(raw_degrees, raw_fields)
