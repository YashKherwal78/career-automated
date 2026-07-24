from typing import List, Dict, Any, Optional, Set, Protocol
from src.career_intelligence.models.capability import Capability

class CapabilityNormalizer(Protocol):
    def normalize(self, name: str) -> str:
        """Normalizes different raw string variations of technology/skills names."""
        ...

class CapabilityMapper(Protocol):
    def map_to_capabilities(self, inputs: List[str]) -> List[Capability]:
        """Maps a collection of input keywords to a list of canonical Capabilities."""
        ...

class CapabilityExtractor(Protocol):
    def extract_from_text(self, text: str) -> List[Capability]:
        """Parses a block of text and returns matching capabilities."""
        ...
