import logging
from typing import List
from src.discovery.search.models import SearchResult
from src.discovery.search.google_provider import GoogleProvider
from src.discovery.search.exa_provider import ExaProvider
from src.common.credential_provider import CredentialFactory

logger = logging.getLogger("SearchManager")

class SearchManager:
    def __init__(self):
        self.providers = []
        
        try:
            exa_provider = ExaProvider(CredentialFactory.get("EXA"))
            self.providers.append(exa_provider)
        except Exception as e:
            logger.warning(f"Could not initialize ExaProvider: {e}")
            
        try:
            google_provider = GoogleProvider(CredentialFactory.get("GOOGLE"))
            self.providers.append(google_provider)
        except Exception as e:
            logger.warning(f"Could not initialize GoogleProvider: {e}")
        
    async def execute_search(self, query: str, limit: int = 10) -> List[SearchResult]:
        all_results = []
        seen_urls = set()
        
        for provider in self.providers:
            try:
                results = await provider.search(query, limit=limit)
                for res in results:
                    # Deduplicate by URL
                    if res.url not in seen_urls:
                        seen_urls.add(res.url)
                        all_results.append(res)
            except Exception as e:
                logger.error(f"Search provider {provider.__class__.__name__} failed on query '{query}': {e}")
                
        return all_results
