import aiohttp
import asyncio
import re
import urllib.parse
from typing import List, Optional
from src.discovery.models import Candidate

from src.discovery.providers.base_provider import DiscoveryStrategy
from src.discovery.providers.provider_registry import ProviderRegistry


class AtsPatternStrategy(DiscoveryStrategy):

    @property
    def base_confidence(self) -> float:
        return 0.60
    """
    Strategy 3 — ATS URL Pattern Guessing.
    
    Generates common ATS board URLs based on the company's name and domain,
    then tests them with a fast GET request. Extremely effective for companies
    that use standard ATS subdomains but don't link them publicly or hide them
    behind JS.
    """

    @property
    def strategy_name(self) -> str:
        return "ats_pattern_guessing"

    # Keep old interface working
    @property
    def provider_name(self) -> str:
        return self.strategy_name

    async def discover(self, company_name: str, website_url: Optional[str] = None) -> List[Candidate]:
        slugs = set()
        
        # 1. Slug from company name (e.g., "Scale AI" -> "scaleai")
        slug1 = re.sub(r'[^a-zA-Z0-9]', '', company_name.lower())
        if slug1:
            slugs.add(slug1)
            
        # 2. Slug from domain (e.g., "stripe.com" -> "stripe")
        if website_url:
            try:
                parsed = urllib.parse.urlparse(website_url if website_url.startswith('http') else f"https://{website_url}")
                domain_parts = parsed.netloc.replace('www.', '').split('.')
                if domain_parts:
                    slugs.add(domain_parts[0])
            except:
                pass

        if not slugs:
            return []

        # Generate candidate URLs
        candidates = []
        for slug in slugs:
            candidates.extend([
                f"https://boards.greenhouse.io/{slug}",
                f"https://jobs.lever.co/{slug}",
                f"https://jobs.ashbyhq.com/{slug}",
                f"https://jobs.smartrecruiters.com/{slug}",
                f"https://{slug}.wd1.myworkdayjobs.com/en-US/{slug}",
                f"https://{slug}.wd3.myworkdayjobs.com/en-US/{slug}",
                f"https://{slug}.wd5.myworkdayjobs.com/en-US/{slug}",
            ])

        valid_urls = []
        headers = {'User-Agent': 'Mozilla/5.0'}
        timeout = aiohttp.ClientTimeout(total=8)
        
        async def check_url(session, url: str) -> Optional[str]:
            try:
                # Need allow_redirects=True to catch lever/greenhouse redirects
                async with session.get(url, headers=headers, allow_redirects=True) as resp:
                    if resp.status == 200:
                        html = (await resp.text()).lower()
                        # Reject soft 404s
                        if "not found" in html or "page not found" in html or "no longer available" in html:
                            return None
                        # Ashby specific soft 404
                        if "ashbyhq.com" in url and ("could not find job board" in html or "no jobs available" in html):
                            return None
                        # Lever specific soft 404
                        if "lever.co" in url and "job board not found" in html:
                            return None
                        return url
            except Exception:
                pass
            return None

        async with aiohttp.ClientSession(timeout=timeout) as session:
            tasks = [check_url(session, url) for url in candidates]
            results = await asyncio.gather(*tasks)
            valid_urls = [url for url in results if url is not None]

        return [Candidate(url=u, source="pattern_guess", source_page="none", depth=0) for u in valid_urls]

    # -- Backwards-compatible aliases ----------------------------------------
    async def search_company(self, company_name: str, website_url: Optional[str] = None) -> List[str]:
        return await self.discover(company_name, website_url)

    async def discover_companies(self, *a, **kw):
        return []

    async def validate(self, session, url: str) -> bool:
        return True

ProviderRegistry.register(AtsPatternStrategy)
