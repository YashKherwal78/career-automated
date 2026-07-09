from src.discovery.providers.provider_registry import ProviderRegistry
import aiohttp
import re
from typing import List
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from src.discovery.providers.base_provider import DiscoveryStrategy
from src.discovery.models import Candidate

class SitemapStrategy(DiscoveryStrategy):
    """
    Parses /sitemap.xml to find careers, jobs, and external ATS URLs.
    """
    
    @property
    def provider_name(self) -> str:
        return self.strategy_name

    @property
    def strategy_name(self) -> str:
        return "sitemap"
        
    async def discover(self, company_name: str, website_url: str) -> List[Candidate]:
        if not website_url:
            return []
            
        website_url = website_url.rstrip('/')
        sitemaps = [
            f"{website_url}/sitemap.xml",
            f"{website_url}/sitemap_index.xml",
            f"{website_url}/sitemap-careers.xml"
        ]
        
        candidates = []
        found_urls = set()
        
        # Regex to detect if a sitemap <loc> contains an ATS token or career path
        ats_pattern = re.compile(r'(greenhouse\.io|lever\.co|ashbyhq\.com|smartrecruiters\.com|myworkdayjobs\.com|/careers|/jobs)', re.IGNORECASE)
        
        async with aiohttp.ClientSession() as session:
            for sitemap_url in sitemaps:
                try:
                    async with session.get(sitemap_url, timeout=5) as response:
                        if response.status != 200:
                            continue
                            
                        content = await response.text()
                        soup = BeautifulSoup(content, 'xml')
                        
                        # Find all <loc> tags
                        for loc in soup.find_all('loc'):
                            url = loc.text.strip()
                            if ats_pattern.search(url):
                                if url not in found_urls:
                                    found_urls.add(url)
                                    candidates.append(Candidate(
                                        url=url,
                                        source=self.strategy_name,
                                        source_page=sitemap_url,
                                        depth=1
                                    ))
                                    
                        # Handle sitemap indexes
                        for sitemap in soup.find_all('sitemap'):
                            loc = sitemap.find('loc')
                            if loc:
                                sub_url = loc.text.strip()
                                if 'career' in sub_url.lower() or 'job' in sub_url.lower():
                                    try:
                                        async with session.get(sub_url, timeout=5) as sub_res:
                                            if sub_res.status == 200:
                                                sub_content = await sub_res.text()
                                                sub_soup = BeautifulSoup(sub_content, 'xml')
                                                for sub_loc in sub_soup.find_all('loc'):
                                                    u = sub_loc.text.strip()
                                                    if u not in found_urls:
                                                        found_urls.add(u)
                                                        candidates.append(Candidate(
                                                            url=u,
                                                            source=self.strategy_name,
                                                            source_page=sub_url,
                                                            depth=2
                                                        ))
                                    except Exception:
                                        pass
                                        
                except Exception:
                    pass
                    
        return candidates

ProviderRegistry.register(SitemapStrategy)
