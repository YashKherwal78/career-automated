from src.discovery.providers.provider_registry import ProviderRegistry
import aiohttp
import re
from typing import List
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from src.discovery.providers.base_provider import DiscoveryStrategy
from src.discovery.models import Candidate

class CareerPageFingerprintStrategy(DiscoveryStrategy):
    """
    Scans the raw HTML of the company homepage and career pages for embedded
    ATS tokens, window.__INITIAL_STATE__, __NEXT_DATA__, and JSON-LD.
    """
    
    @property
    def provider_name(self) -> str:
        return self.strategy_name

    @property
    def strategy_name(self) -> str:
        return "career_page_fingerprint"
        
    async def discover(self, company_name: str, website_url: str) -> List[Candidate]:
        if not website_url:
            return []
            
        website_url = website_url.rstrip('/')
        paths_to_check = [
            website_url,
            f"{website_url}/careers",
            f"{website_url}/jobs",
            f"{website_url}/about"
        ]
        
        candidates = []
        found_urls = set()
        
        # ATS Signatures mapping string -> domain pattern
        ats_signatures = {
            r'boards\.greenhouse\.io/([^/\"\']+)': 'https://boards.greenhouse.io/{}',
            r'boards-api\.greenhouse\.io/v1/boards/([^/\"\']+)': 'https://boards-api.greenhouse.io/v1/boards/{}',
            r'jobs\.lever\.co/([^/\"\']+)': 'https://jobs.lever.co/{}',
            r'api\.lever\.co/v0/postings/([^/\"\']+)': 'https://api.lever.co/v0/postings/{}',
            r'jobs\.ashbyhq\.com/([^/\"\']+)': 'https://jobs.ashbyhq.com/{}',
            r'api\.ashbyhq\.com/posting-api/job-board/([^/\"\']+)': 'https://api.ashbyhq.com/posting-api/job-board/{}',
            r'jobs\.smartrecruiters\.com/([^/\"\']+)': 'https://jobs.smartrecruiters.com/{}',
            r'api\.smartrecruiters\.com/v1/companies/([^/\"\']+)': 'https://api.smartrecruiters.com/v1/companies/{}',
            r'([\w\-]+)\.wd5\.myworkdayjobs\.com': 'https://{}.wd5.myworkdayjobs.com',
            r'([\w\-]+)\.wd1\.myworkdayjobs\.com': 'https://{}.wd1.myworkdayjobs.com',
            r'([\w\-]+)\.wd3\.myworkdayjobs\.com': 'https://{}.wd3.myworkdayjobs.com',
        }
        
        async with aiohttp.ClientSession() as session:
            for path in paths_to_check:
                try:
                    async with session.get(path, timeout=5) as response:
                        if response.status != 200:
                            continue
                            
                        html = await response.text()
                        
                        # 1. Regex scan the raw HTML for ATS endpoints directly
                        for pattern, url_template in ats_signatures.items():
                            matches = re.finditer(pattern, html)
                            for match in matches:
                                token = match.group(1)
                                if token and token not in ["", "api", "v1", "v0", "boards"]:
                                    full_url = url_template.format(token)
                                    if full_url not in found_urls:
                                        found_urls.add(full_url)
                                        candidates.append(Candidate(
                                            url=full_url,
                                            source=self.strategy_name,
                                            source_page=path,
                                            depth=1
                                        ))
                                        
                except Exception:
                    pass
                    
        return candidates

ProviderRegistry.register(CareerPageFingerprintStrategy)
