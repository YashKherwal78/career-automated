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
        """
        Normalize an Ashby URL to the board-level URL.

        Input examples:
          https://jobs.ashbyhq.com/Linear/820d0d5a-0930-475c-b494-23e18ad2aa68
          https://jobs.ashbyhq.com/Linear/820d0d5a-0930-475c-b494-23e18ad2aa68/application
          https://jobs.ashbyhq.com/Linear?utm_source=github
        Output:
          https://jobs.ashbyhq.com/Linear
        """
        import re
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(endpoint)
        # Keep only the first non-empty path segment (the company/board slug).
        # Strip UUIDs (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx) and anything after them.
        path = parsed.path.rstrip('/')
        # Remove /application suffix
        path = re.sub(r'/application$', '', path, flags=re.IGNORECASE)
        # Remove UUID path segments (and anything after)
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}.*$',
            '', path, flags=re.IGNORECASE
        )
        # Keep scheme + host + board slug only (no query, no fragment)
        canonical = urlunparse((parsed.scheme, parsed.netloc, path, '', '', ''))
        return canonical

    async def health_check(self, endpoint: str) -> bool:
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(endpoint, timeout=5, allow_redirects=True) as resp:
                    return resp.status < 400
        except Exception:
            return False
