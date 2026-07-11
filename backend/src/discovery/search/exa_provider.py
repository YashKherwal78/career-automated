import os
import time
import aiohttp
from typing import List
from src.discovery.search.models import SearchResult
from src.discovery.search.base import SearchProvider
from src.common.credential_provider import CredentialProvider, Credential, RateLimitException, AuthException

class ExaProvider(SearchProvider):
    def __init__(self, credentials: CredentialProvider):
        self.credentials = credentials
        self.base_url = "https://api.exa.ai/search"
        
    async def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        start_time = time.time()
        
        payload = {
            "query": query,
            "numResults": limit,
            "type": "keyword"
        }
        
        async def fetch(credential: Credential):
            headers = {
                "x-api-key": credential.secret,
                "Content-Type": "application/json"
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=payload) as response:
                    if response.status == 429:
                        raise RateLimitException()
                    elif response.status in [401, 403]:
                        raise AuthException()
                        
                    if response.status == 200:
                        return await response.json()
                    
                    print(f"[ExaProvider] Error: {response.status}")
                    return None
                    
        try:
            data = await self.credentials.execute(fetch)
            if not data:
                return []
                
            items = data.get("results", [])
            latency = int((time.time() - start_time) * 1000)
            
            results = []
            for idx, item in enumerate(items):
                results.append(SearchResult(
                    provider="exa",
                    query=query,
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("text", ""),
                    rank=idx + 1,
                    latency_ms=latency
                ))
            return results
        except Exception as e:
            print(f"[ExaProvider] Exception: {e}")
            return []
