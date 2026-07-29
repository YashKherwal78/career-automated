import time
import aiohttp
from typing import List
from src.discovery.search.models import SearchResult
from src.discovery.search.base import SearchProvider
from src.common.credential_provider import CredentialProvider, Credential, RateLimitException, AuthException


class BraveProvider(SearchProvider):
    """Brave Search API — free tier (2,000 queries/month as of writing), no card required historically."""

    def __init__(self, credentials: CredentialProvider):
        self.credentials = credentials
        self.base_url = "https://api.search.brave.com/res/v1/web/search"

    async def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        start_time = time.time()

        async def fetch(credential: Credential):
            headers = {
                "Accept": "application/json",
                "X-Subscription-Token": credential.secret,
            }
            params = {"q": query, "count": min(limit, 20)}

            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, headers=headers, params=params) as response:
                    if response.status == 429:
                        raise RateLimitException()
                    elif response.status in (401, 403):
                        raise AuthException()

                    if response.status == 200:
                        return await response.json()

                    print(f"[BraveProvider] Error: {response.status}")
                    return None

        try:
            data = await self.credentials.execute(fetch)
            if not data:
                return []

            items = (data.get("web") or {}).get("results", [])
            latency = int((time.time() - start_time) * 1000)

            results = []
            for idx, item in enumerate(items):
                results.append(SearchResult(
                    provider="brave",
                    query=query,
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                    rank=idx + 1,
                    latency_ms=latency,
                ))
            return results
        except Exception as e:
            print(f"[BraveProvider] Exception: {e}")
            return []
