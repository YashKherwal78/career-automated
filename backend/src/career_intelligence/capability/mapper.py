from typing import List
from src.career_intelligence.capability.interfaces import CapabilityMapper, CapabilityNormalizer
from src.career_intelligence.capability.registry import CapabilityRegistry
from src.career_intelligence.models.capability import Capability

class DefaultCapabilityMapper(CapabilityMapper):
    def __init__(self, registry: CapabilityRegistry, normalizer: CapabilityNormalizer):
        self.registry = registry
        self.normalizer = normalizer

    def map_to_capabilities(self, inputs: List[str]) -> List[Capability]:
        """Maps a collection of input keywords to a list of canonical Capabilities."""
        resolved = []
        seen_ids = set()
        
        for inp in inputs:
            norm_name = self.normalizer.normalize(inp)
            caps = self.registry.lookup(norm_name)
            for cap in caps:
                if cap.id not in seen_ids:
                    resolved.append(cap)
                    seen_ids.add(cap.id)
                    
        return resolved
