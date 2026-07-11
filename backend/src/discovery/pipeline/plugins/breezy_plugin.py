from typing import List, Optional, Tuple, Any
from src.discovery.pipeline.fallback_models import DiscoveryPlugin
from src.discovery.models import BoardIdentity
from src.discovery.inspectors.base_inspector import SourceInspector
from src.discovery.inspectors.breezy_inspector import BreezyInspector
from src.discovery.pipeline.parsers import BreezyParser

class BreezyDiscoveryPlugin(DiscoveryPlugin):
    def __init__(self):
        self.parser = BreezyParser()

    @property
    def provider_name(self) -> str:
        return "breezy"
        
    def candidate_domains(self) -> List[str]:
        return ["breezy.hr"]
        
    def fingerprints(self) -> List[str]:
        return [
            "breezy.hr"
        ]
        
    def parse_candidate(self, url: str) -> Tuple[Optional[BoardIdentity], float, Optional[str]]:
        return self.parser.parse(url)
        
    def inspector(self) -> SourceInspector:
        return BreezyInspector()
        
    def confidence(self, evidence: Any) -> float:
        return 1.0

    def canonicalize(self, endpoint: str) -> str:
        canon = endpoint.split('?')[0].strip('/')
        return canon

    async def health_check(self, endpoint: str) -> bool:
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(endpoint, timeout=5, allow_redirects=True) as resp:
                    return resp.status < 400
        except Exception:
            return False
