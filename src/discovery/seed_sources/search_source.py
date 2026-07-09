import logging
import re
from typing import List, Dict, Any
from urllib.parse import urlparse
from src.discovery.seed_sources.base import SeedSource
from src.discovery.search.provider_manager import SearchManager

logger = logging.getLogger("SearchSource")

class SearchSource(SeedSource):
    name = "search"
    priority = 2
    enabled = True

    def __init__(self):
        self.search_manager = SearchManager()

    async def discover(self) -> List[Dict[str, Any]]:
        logger.info("Discovering company seeds from SearchSource fallback...")
        
        # High quality queries to search for startup sites
        queries = [
            "site:greenhouse.io tech startup jobs",
            "site:lever.co software engineer remote jobs",
            "site:ashbyhq.com software engineer jobs"
        ]
        
        discovered_seeds = []
        for q in queries:
            try:
                results = await self.search_manager.execute_search(q, limit=10)
                for r in results:
                    # Parse domain out of result URL
                    parsed = urlparse(r.url)
                    netloc = parsed.netloc.lower()
                    
                    # Skip common service/ATS domains
                    if any(ats in netloc for ats in ["greenhouse.io", "lever.co", "ashbyhq.com", "google.com", "github.com"]):
                        continue
                        
                    domain = netloc.replace("www.", "")
                    if domain:
                        company_id = domain.split(".")[0]
                        # Try to construct a clean name
                        clean_name = r.title.split("|")[0].split("-")[0].strip()
                        # Clean up name if it's too long
                        if len(clean_name) > 30:
                            clean_name = company_id.capitalize()
                            
                        discovered_seeds.append({
                            "company_id": company_id,
                            "name": clean_name,
                            "website": f"https://{domain}",
                            "source": "search",
                            "confidence": 0.7
                        })
            except Exception as e:
                logger.error(f"SearchSource query '{q}' failed: {e}")
                
        return discovered_seeds
