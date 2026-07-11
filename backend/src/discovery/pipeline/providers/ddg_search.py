import asyncio
from typing import List
from src.discovery.pipeline.search_provider import SearchProvider, SearchResult
import warnings

class DuckDuckGoSearchProvider(SearchProvider):
    async def search(self, query: str) -> List[SearchResult]:
        try:
            # Handle the warning gracefully
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    from ddgs import DDGS
                except ImportError:
                    from duckduckgo_search import DDGS
        except ImportError:
            return []
            
        def _search():
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=3))
                
        loop = asyncio.get_event_loop()
        try:
            # Added a short timeout for DDG since it tends to hang
            results = await asyncio.wait_for(loop.run_in_executor(None, _search), timeout=5.0)
        except Exception:
            return []
            
        parsed_results = []
        for r in results:
            parsed_results.append(SearchResult(
                url=r.get('href', ''),
                title=r.get('title', ''),
                snippet=r.get('body', '')
            ))
            
        return parsed_results
