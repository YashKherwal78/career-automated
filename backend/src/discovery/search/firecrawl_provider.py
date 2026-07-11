import time
import aiohttp
from typing import List
from src.discovery.search.models import SearchResult
from src.common.credential_provider import CredentialProvider, Credential, RateLimitException, AuthException

class FirecrawlProvider:
    def __init__(self, credentials: CredentialProvider):
        self.credentials = credentials
        self.base_url = "https://api.firecrawl.dev/v1/scrape"
        
    async def extract(self, url: str) -> List[SearchResult]:
        start_time = time.time()
        
        payload = {
            "url": url,
            "formats": ["links"],
            "onlyMainContent": False
        }
        
        async def fetch(credential: Credential):
            headers = {
                "Authorization": f"Bearer {credential.secret}",
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
                    
                    print(f"[FirecrawlProvider] Error: {response.status}")
                    return None
                    
        try:
            data = await self.credentials.execute(fetch)
            if not data:
                return []
                
            scrape_data = data.get("data", {})
            links = scrape_data.get("links", [])
            metadata = scrape_data.get("metadata", {})
            
            latency = int((time.time() - start_time) * 1000)
            title = metadata.get("title", "")
            
            results = []
            for idx, link in enumerate(links):
                results.append(SearchResult(
                    provider="firecrawl",
                    query=f"extract:{url}",
                    title=title,
                    url=link,
                    snippet="Extracted via Firecrawl",
                    rank=idx + 1,
                    latency_ms=latency
                ))
            return results
        except Exception as e:
            print(f"[FirecrawlProvider] Exception: {e}")
            return []
