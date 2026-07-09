from typing import List, Optional, Tuple, Any
from src.discovery.pipeline.fallback_models import DiscoveryPlugin
from src.discovery.models import BoardIdentity
from src.discovery.inspectors.base_inspector import SourceInspector
from src.discovery.inspectors.ashby_inspector import AshbyInspector
from src.discovery.pipeline.parsers import AshbyParser

class AshbyDiscoveryPlugin(DiscoveryPlugin):
    def __init__(self):
        self.parser = AshbyParser()

    @property
    def provider_name(self) -> str:
        return "ashby"
        
    def candidate_domains(self) -> List[str]:
        return ["jobs.ashbyhq.com", "ashbyhq.com"]
        
    def fingerprints(self) -> List[str]:
        return [
            "ashbyhq.com"
        ]
        
    def parse_candidate(self, url: str) -> Tuple[Optional[BoardIdentity], float, Optional[str]]:
        return self.parser.parse(url)
        
    def inspector(self) -> SourceInspector:
        return AshbyInspector()
        
    def confidence(self, evidence: Any) -> float:
        return 1.0

    def canonicalize(self, endpoint: str) -> str:
        import re
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
