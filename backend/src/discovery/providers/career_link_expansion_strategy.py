from src.discovery.providers.provider_registry import ProviderRegistry
import aiohttp
import re
from typing import List, Set
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from src.discovery.providers.base_provider import DiscoveryStrategy
from src.discovery.models import Candidate

class CareerLinkExpansionStrategy(DiscoveryStrategy):
    """
    Replaces the generic BFS crawler. Extracts targeted internal links (About, Careers, Team)
    and crawls them to find ATS external endpoints (Greenhouse, Lever, Ashby, etc.).
    """
    
    @property
    def provider_name(self) -> str:
        return self.strategy_name

    @property
    def strategy_name(self) -> str:
        return "career_link_expansion"
        
    async def discover(self, company_name: str, website_url: str) -> List[Candidate]:
        if not website_url:
            return []
            
        website_url = website_url.rstrip('/')
        candidates = []
        found_ats_urls = set()
        
        # Internal paths to fetch
        paths_to_crawl = {website_url}
        crawled_paths = set()
        
        # Regexes for finding promising internal links
        internal_keyword_pattern = re.compile(r'(career|job|about|team|company|join|work|people)', re.IGNORECASE)
        
        # Known ATS patterns
        ats_pattern = re.compile(r'(greenhouse\.io|lever\.co|ashbyhq\.com|smartrecruiters\.com|myworkdayjobs\.com)', re.IGNORECASE)
        
        async with aiohttp.ClientSession() as session:
            # 1. Fetch homepage to find internal career links
            try:
                async with session.get(website_url, timeout=5) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        for a in soup.find_all('a', href=True):
                            href = a['href']
                            text = a.text.strip()
                            
                            # Is it an external ATS link?
                            if ats_pattern.search(href):
                                if href not in found_ats_urls:
                                    found_ats_urls.add(href)
                                    candidates.append(Candidate(
                                        url=href,
                                        source=self.strategy_name,
                                        source_page=website_url,
                                        depth=1
                                    ))
                                continue
                                
                            # Is it an internal career link?
                            if internal_keyword_pattern.search(href) or internal_keyword_pattern.search(text):
                                full_url = urljoin(website_url, href)
                                if full_url.startswith(website_url) and full_url not in crawled_paths:
                                    paths_to_crawl.add(full_url)
            except Exception:
                pass
                
            crawled_paths.add(website_url)
            
            # 2. Fetch the discovered internal career pages to find ATS links
            for path in list(paths_to_crawl):
                if path in crawled_paths:
                    continue
                crawled_paths.add(path)
                
                try:
                    async with session.get(path, timeout=5) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            for a in soup.find_all('a', href=True):
                                href = a['href']
                                
                                if ats_pattern.search(href):
                                    if href not in found_ats_urls:
                                        found_ats_urls.add(href)
                                        candidates.append(Candidate(
                                            url=href,
                                            source=self.strategy_name,
                                            source_page=path,
                                            depth=2
                                        ))
                except Exception:
                    pass
                    
        return candidates

ProviderRegistry.register(CareerLinkExpansionStrategy)
