from src.discovery.models import Candidate
import aiohttp
import asyncio
import re
import urllib.parse
from typing import List, Dict, Any, Optional

from src.discovery.providers.base_provider import DiscoveryStrategy
from src.discovery.providers.provider_registry import ProviderRegistry


# ---------------------------------------------------------------------------
# Search Backends
# ---------------------------------------------------------------------------

class SearchBackend:
    """Abstract search backend. Returns raw URLs from a search engine."""
    async def search(self, query: str) -> List[str]:
        raise NotImplementedError()


class YahooBackend(SearchBackend):
    async def search(self, query: str) -> List[str]:
        urls: list[str] = []
        try:
            search_url = f"https://search.yahoo.com/search?p={urllib.parse.quote(query)}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                              'AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/122.0.0.0 Safari/537.36'
            }
            timeout = aiohttp.ClientTimeout(total=12)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(search_url, headers=headers) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        # Yahoo wraps outbound links as RU=<encoded_url>/
                        ru_matches = re.findall(r'RU=([^/]+)/', html)
                        urls.extend(urllib.parse.unquote(m) for m in ru_matches)
                        # Direct hrefs as fallback
                        direct = re.findall(r'href="(https?://[^"]+)"', html)
                        urls.extend(m for m in direct if 'yahoo.com' not in m)
        except Exception as e:
            pass
        return list(set(urls))


class DuckDuckGoBackend(SearchBackend):
    """Currently rate-limited (202 anti-bot). Kept as dormant fallback."""
    async def search(self, query: str) -> List[str]:
        return []


class BingBackend(SearchBackend):
    """Currently broken (primp impersonation failure). Kept as dormant fallback."""
    async def search(self, query: str) -> List[str]:
        return []


# ---------------------------------------------------------------------------
# Search Strategy
# ---------------------------------------------------------------------------

class SearchStrategy(DiscoveryStrategy):

    @property
    def base_confidence(self) -> float:
        return 0.80
    """
    Strategy 2 — Search Engine Discovery.

    Issues multiple atomic queries per company (no OR operators) across
    pluggable search backends. Has zero ATS knowledge.
    """

    def __init__(self):
        self.backends: list[SearchBackend] = [
            YahooBackend(),
            DuckDuckGoBackend(),
            BingBackend(),
        ]

    @property
    def strategy_name(self) -> str:
        return "search_engine"

    # Backwards-compatible alias
    @property
    def provider_name(self) -> str:
        return self.strategy_name

    async def discover(self, company_name: str, website_url: Optional[str] = None) -> List[Candidate]:
        # Atomic queries — no OR operators
        queries = [
            f'"{company_name}" careers',
            f'"{company_name}" jobs',
            f'"{company_name}" apply',
        ]

        all_urls: list[str] = []
        for backend in self.backends:
            for query in queries:
                results = await backend.search(query)
                if results:
                    all_urls.extend(results)
            # If a backend returned anything, stop trying others
            if all_urls:
                break

        return list(set(all_urls))

    # -- Backwards-compatible aliases for the old orchestrator ---------------
    async def search_company(self, company_name: str, website_url: Optional[str] = None) -> List[str]:
        return await self.discover(company_name, website_url)

    async def discover_companies(self, *a, **kw):
        return []

    async def validate(self, session, url: str) -> bool:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            async with session.get(url, headers=headers, timeout=10, allow_redirects=True) as resp:
                return resp.status in [200, 403, 406]
        except Exception:
            return False


ProviderRegistry.register(SearchStrategy)
