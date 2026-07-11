import time
import aiohttp
from typing import List
from src.discovery.search.models import SearchResult
from src.discovery.search.base import SearchProvider
from src.common.credential_provider import CredentialProvider, Credential, RateLimitException, AuthException

class GoogleProvider(SearchProvider):
    def __init__(self, credentials: CredentialProvider):
        self.credentials = credentials
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
    async def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        start_time = time.time()
        
        async def fetch(credential: Credential):
            cx = credential.config.get("cx")
            if not cx:
                raise ValueError(f"Google Credential {credential.id} is missing CX in config.")
                
            params = {
                "key": credential.secret,
                "cx": cx,
                "q": query,
                "num": min(limit, 10)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 429:
                        raise RateLimitException()
                    elif response.status in [401, 403]:
                        raise AuthException()
                        
                    if response.status == 200:
                        return await response.json()
                    
                    print(f"[GoogleProvider] Error: {response.status}")
                    return None
                    
        try:
            data = await self.credentials.execute(fetch)
            if not data:
                return []
                
            items = data.get("items", [])
            latency = int((time.time() - start_time) * 1000)
            
            results = []
            for idx, item in enumerate(items):
                results.append(SearchResult(
                    provider="google",
                    query=query,
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    rank=idx + 1,
                    latency_ms=latency
                ))
            return results
        except Exception as e:
            print(f"[GoogleProvider] Exception: {e}")
            return []
