from src.discovery.providers.provider_registry import ProviderRegistry
import aiohttp
import re
from typing import List
from urllib.parse import urljoin

from src.discovery.providers.base_provider import DiscoveryStrategy
from src.discovery.models import Candidate

class RobotsTxtStrategy(DiscoveryStrategy):
    """
    Parses /robots.txt to find Sitemap directives and blocked /jobs paths.
    """
    
    @property
    def provider_name(self) -> str:
        return self.strategy_name

    @property
    def strategy_name(self) -> str:
        return "robots_txt"
        
    async def discover(self, company_name: str, website_url: str) -> List[Candidate]:
        if not website_url:
            return []
            
        website_url = website_url.rstrip('/')
        robots_url = f"{website_url}/robots.txt"
        
        candidates = []
        found_urls = set()
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(robots_url, timeout=5) as response:
                    if response.status != 200:
                        return candidates
                        
                    content = await response.text()
                    
                    for line in content.splitlines():
                        line = line.strip()
                        if line.lower().startswith("sitemap:"):
                            parts = line.split(":", 1)
                            if len(parts) == 2:
                                sitemap_url = parts[1].strip()
                                # Instead of downloading the sitemap here, we just yield it as a candidate.
                                # Wait, candidates are supposed to be ATS endpoints.
                                # If we find a sitemap, we don't know the ATS yet.
                                # But actually, SitemapStrategy handles sitemaps. 
                                # Maybe RobotsTxtStrategy should just find ATS links if they are leaked in Disallow?
                                pass
                                
                        elif line.lower().startswith("disallow:"):
                            parts = line.split(":", 1)
                            if len(parts) == 2:
                                path = parts[1].strip()
                                # Some companies block /jobs or their direct ATS proxy
                                if "job" in path.lower() or "career" in path.lower():
                                    full_url = urljoin(website_url, path)
                                    if full_url not in found_urls:
                                        found_urls.add(full_url)
                                        candidates.append(Candidate(
                                            url=full_url,
                                            source=self.strategy_name,
                                            source_page=robots_url,
                                            depth=1
                                        ))
            except Exception:
                pass
                
        return candidates

ProviderRegistry.register(RobotsTxtStrategy)
