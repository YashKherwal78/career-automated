from typing import Protocol, List
from ddgs import DDGS
import asyncio

class SearchProvider(Protocol):
    async def search_ats_links(self, company_name: str, ats_domain: str) -> List[str]: ...

class DuckDuckGoSearchProvider:
    def __init__(self):
        pass
        
    async def search_ats_links(self, company_name: str, ats_domain: str) -> List[str]:
        query = f'site:{ats_domain} "{company_name}"'
        try:
            def _sync_search():
                with DDGS() as ddgs:
                    results = ddgs.text(query, max_results=3)
                    return [res['href'] for res in results]
            
            return await asyncio.to_thread(_sync_search)
        except Exception as e:
            return []

class SearchProviderRegistry:
    def __init__(self):
        self.providers = {
            "duckduckgo": DuckDuckGoSearchProvider()
        }
        
    def get_provider(self, name: str) -> SearchProvider:
        return self.providers.get(name.lower(), self.providers["duckduckgo"])
