import asyncio
import time
from typing import List
from ddgs import DDGS
from src.discovery.search.models import SearchResult
from src.discovery.search.base import SearchProvider


class DDGSProvider(SearchProvider):
    """
    DuckDuckGo search via the ddgs library — no API key, no signup, no
    per-query cost. Used as the primary/always-available search source;
    Exa/Google (paid, quota-limited) supplement it rather than the other
    way around.
    """

    async def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        start_time = time.time()
        try:
            raw_results = await asyncio.to_thread(
                lambda: DDGS().text(query, max_results=limit)
            )
        except Exception as e:
            print(f"[DDGSProvider] Exception: {e}")
            return []

        latency = int((time.time() - start_time) * 1000)
        results = []
        for idx, item in enumerate(raw_results or []):
            results.append(SearchResult(
                provider="ddgs",
                query=query,
                title=item.get("title", ""),
                url=item.get("href", ""),
                snippet=item.get("body", ""),
                rank=idx + 1,
                latency_ms=latency,
            ))
        return results
