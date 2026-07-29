import logging
from typing import List
from src.discovery.search.models import SearchResult
from src.discovery.search.ddgs_provider import DDGSProvider
from src.discovery.search.brave_provider import BraveProvider
from src.discovery.search.google_provider import GoogleProvider
from src.discovery.search.exa_provider import ExaProvider
from src.common.credential_provider import CredentialFactory
from src.common.api_cascader import ApiCascader, CascadeProvider

logger = logging.getLogger("SearchManager")

class SearchManager:
    def __init__(self):
        self._seen_urls = set()
        cascade_providers = []

        # Free-first cascade: DDGS and Brave cost nothing and have no
        # meaningful quota concern at our volume, so they're tried before
        # ever spending Exa/Google quota. Each is only added to the cascade
        # if it actually initializes (e.g. Brave/Google no-op silently until
        # their API keys are added to .env — see BRAVE_API_KEY, GOOGLE_CX).
        try:
            ddgs = DDGSProvider()
            cascade_providers.append(CascadeProvider("ddgs", self._wrap(ddgs), free=True))
        except Exception as e:
            logger.warning(f"Could not initialize DDGSProvider: {e}")

        try:
            brave = BraveProvider(CredentialFactory.get("BRAVE"))
            cascade_providers.append(CascadeProvider("brave", self._wrap(brave), free=True))
        except Exception as e:
            logger.warning(f"Could not initialize BraveProvider: {e}")

        try:
            exa = ExaProvider(CredentialFactory.get("EXA"))
            cascade_providers.append(CascadeProvider("exa", self._wrap(exa), free=False))
        except Exception as e:
            logger.warning(f"Could not initialize ExaProvider: {e}")

        try:
            google = GoogleProvider(CredentialFactory.get("GOOGLE"))
            cascade_providers.append(CascadeProvider("google", self._wrap(google), free=False))
        except Exception as e:
            logger.warning(f"Could not initialize GoogleProvider: {e}")

        self.providers = [p for p in [
            next((cp for cp in cascade_providers if cp.name == n), None)
            for n in ("ddgs", "brave", "exa", "google")
        ] if p]
        self.cascader: ApiCascader[SearchResult] = ApiCascader(self.providers)

    def _wrap(self, provider):
        """Adapts a SearchProvider's .search(query, limit) into the
        cascader's positional-args call convention, deduping by URL across
        cascade steps so a later provider doesn't re-add the same result."""
        async def call(query: str, limit: int = 10):
            results = await provider.search(query, limit=limit)
            deduped = []
            for r in results:
                if r.url not in self._seen_urls:
                    self._seen_urls.add(r.url)
                    deduped.append(r)
            return deduped
        return call

    async def execute_search(self, query: str, limit: int = 10) -> List[SearchResult]:
        self._seen_urls = set()
        return await self.cascader.execute(query, limit=limit, min_results=limit)
