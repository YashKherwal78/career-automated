import aiohttp
import os
import json
from typing import List
from src.discovery.pipeline.search_provider import SearchProvider, SearchResult

class SerperSearchProvider(SearchProvider):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("SERPER_API_KEY", "")
        
    async def search(self, query: str) -> List[SearchResult]:
        if not self.api_key:
            return []
            
        url = "https://google.serper.dev/search"
        payload = json.dumps({"q": query, "num": 5})
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, data=payload, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []
                        for item in data.get("organic", []):
                            results.append(SearchResult(
                                url=item.get("link", ""),
                                title=item.get("title", ""),
                                snippet=item.get("snippet", "")
                            ))
                        return results
                    return []
            except Exception:
                return []
