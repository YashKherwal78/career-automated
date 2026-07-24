import re
from typing import List
from src.career_intelligence.capability.interfaces import CapabilityExtractor, CapabilityMapper
from src.career_intelligence.capability.registry import CapabilityRegistry
from src.career_intelligence.models.capability import Capability

class DefaultCapabilityExtractor(CapabilityExtractor):
    def __init__(self, registry: CapabilityRegistry, mapper: CapabilityMapper):
        self.registry = registry
        self.mapper = mapper

    def extract_from_text(self, text: str) -> List[Capability]:
        """Scans raw text block to match registered capability keywords."""
        if not text:
            return []
            
        found_keywords = []
        text_lower = text.lower()
        
        # Simple scan of registered keys
        for key in self.registry.mappings.keys():
            # Check boundary match
            pattern = r'\b' + re.escape(key) + r'\b'
            if re.search(pattern, text_lower):
                found_keywords.append(key)
                
        # Scans for explicit verb phrases as fallback capability cues
        phrases = {
            "rest api": "fastapi",
            "backend service": "nodejs",
            "container": "docker",
            "microservice": "fastapi"
        }
        for phrase, fallback_key in phrases.items():
            if phrase in text_lower:
                found_keywords.append(fallback_key)

        return self.mapper.map_to_capabilities(found_keywords)
