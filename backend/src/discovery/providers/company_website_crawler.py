import aiohttp
import asyncio
import re
import urllib.parse
from typing import List, Optional
from src.discovery.models import Candidate

from src.discovery.providers.base_provider import DiscoveryStrategy
from src.discovery.providers.provider_registry import ProviderRegistry


# ---------------------------------------------------------------------------
# URL extractor — scans the ENTIRE HTML body for anything that looks like a URL.
# This catches hrefs, script tags, JSON blobs, __NEXT_DATA__, JSON-LD, etc.
# The strategy has ZERO knowledge of which URLs are ATS endpoints.
# ---------------------------------------------------------------------------
_URL_RE = re.compile(
    r'https?://[a-zA-Z0-9\-]+(?:\.[a-zA-Z0-9\-]+)+(?:[/][^\s"\'<>{}|\\^`\[\]]*)?'
)

_CAREER_KEYWORDS = frozenset([
    'career', 'careers', 'job', 'jobs', 'apply', 'join',
    'work-with-us', 'openings', 'opportunities', 'talent',
    'hiring', 'vacancies', 'positions',
])


def _extract_all_urls(html: str) -> List[str]:
    """Pull every URL-shaped string from the full HTML source."""
    return list(set(_URL_RE.findall(html)))


def _is_career_link(href: str, anchor_text: str) -> bool:
    """Heuristic: does this anchor look like a career/jobs page?"""
    combined = (href + ' ' + anchor_text).lower()
    return any(kw in combined for kw in _CAREER_KEYWORDS)


class WebsiteCrawlerStrategy(DiscoveryStrategy):

    @property
    def base_confidence(self) -> float:
        return 0.95
    """
    Strategy 1 — Direct Company Website Crawl.

    Crawls the company's own domain to a depth of 2:
        homepage → internal pages (about, company) → career pages

    Extracts ALL URLs from the full HTML of every visited page and returns
    them as raw candidates. Has zero knowledge of ATS platforms.
    """

    @property
    def strategy_name(self) -> str:
        return "website_crawler"

    # Keep old interface working
    @property
    def provider_name(self) -> str:
        return self.strategy_name

    async def discover(self, company_name: str, website_url: Optional[str] = None) -> List[Candidate]:
        if not website_url:
            return []

        if not website_url.startswith('http'):
            website_url = 'https://' + website_url

        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/122.0.0.0 Safari/537.36'
            )
        }

        all_candidate_urls: set[str] = set()
        visited: set[str] = set()
        timeout = aiohttp.ClientTimeout(total=12)

        # Common career page paths. Many SPA homepages are JS-rendered and
        # have zero <a> tags in the SSR HTML, but /careers and /jobs often
        # return server-rendered pages with ATS embed URLs.
        _COMMON_PATHS = [
            '/careers', '/jobs', '/about/careers', '/company/careers',
            '/about/jobs', '/join', '/openings', '/work-with-us',
        ]

        async with aiohttp.ClientSession(timeout=timeout) as session:

            # ---- Phase 0: Probe common career paths directly ---------------
            # This is the single highest-recall step. It works even when
            # the homepage is a full SPA with no SSR links.
            base = website_url.rstrip('/')
            for path in _COMMON_PATHS:
                probe_url = base + path
                if probe_url in visited:
                    continue
                visited.add(probe_url)
                html = await self._fetch_page(session, probe_url, headers)
                if html:
                    all_candidate_urls.update(_extract_all_urls(html))

            # ---- Phase 1: Homepage -----------------------------------------
            homepage_html = await self._fetch_page(session, website_url, headers)
            if homepage_html:
                visited.add(website_url)
                all_candidate_urls.update(_extract_all_urls(homepage_html))

                # Find internal links that look like career pages OR generic
                # internal pages (about, company) that might link to careers.
                depth1_links = self._find_internal_links(
                    homepage_html, website_url, visited
                )

                # ---- Phase 2: Internal pages (depth 1) ---------------------
                depth2_queue: list[str] = []
                for link in depth1_links[:8]:   # cap breadth
                    if link in visited:
                        continue
                    visited.add(link)
                    html = await self._fetch_page(session, link, headers)
                    if not html:
                        continue
                    all_candidate_urls.update(_extract_all_urls(html))

                    # Collect career-looking links for depth 2
                    for sub in self._find_career_links(html, link, visited):
                        if sub not in visited:
                            depth2_queue.append(sub)

                # ---- Phase 3: Career sub-pages (depth 2) -------------------
                for link in list(set(depth2_queue))[:5]:   # cap breadth
                    if link in visited:
                        continue
                    visited.add(link)
                    html = await self._fetch_page(session, link, headers)
                    if not html:
                        continue
                    all_candidate_urls.update(_extract_all_urls(html))

        return [Candidate(url=u, source="crawler", source_page=website_url or company_name, depth=1) for u in all_candidate_urls]

    # -- Backwards-compatible aliases for the old orchestrator ---------------
    async def search_company(self, company_name: str, website_url: Optional[str] = None) -> List[str]:
        return await self.discover(company_name, website_url)

    async def discover_companies(self, *a, **kw):
        return []

    async def validate(self, session, url: str) -> bool:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            async with session.get(url, headers=headers, timeout=10, allow_redirects=True) as resp:
                return resp.status in [200, 406]
        except Exception:
            return False

    # -- Helpers -------------------------------------------------------------

    @staticmethod
    async def _fetch_page(session, url: str, headers: dict) -> Optional[str]:
        try:
            async with session.get(url, headers=headers, allow_redirects=True) as resp:
                if resp.status == 200:
                    return await resp.text()
        except Exception:
            pass
        return None

    @staticmethod
    def _find_internal_links(html: str, base_url: str, visited: set) -> List[str]:
        """Find internal pages worth visiting (career pages + about/company)."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        base_domain = urllib.parse.urlparse(base_url).netloc

        links = []
        for a in soup.find_all('a', href=True):
            href = a['href'].split('#')[0].split('?')[0].rstrip('/')
            if not href:
                continue
            # Resolve relative
            if href.startswith('/'):
                href = urllib.parse.urljoin(base_url, href)
            if not href.startswith('http'):
                continue
            # Must be same domain (internal)
            if urllib.parse.urlparse(href).netloc != base_domain:
                # But external career links are also interesting
                if _is_career_link(href, a.get_text()):
                    links.append(href)
                continue
            if href in visited:
                continue
            text = a.get_text().lower()
            combined = (href + ' ' + text).lower()
            # Prioritize career-like pages, but also grab about/company/team
            if any(kw in combined for kw in [
                'career', 'job', 'jobs', 'apply', 'openings', 'hiring',
                'about', 'company', 'team', 'work', 'talent', 'join',
                'opportunities', 'vacancies', 'positions',
            ]):
                links.append(href)
        return list(set(links))

    @staticmethod
    def _find_career_links(html: str, base_url: str, visited: set) -> List[str]:
        """From a depth-1 page, find links that specifically look like career pages."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href'].split('#')[0].split('?')[0].rstrip('/')
            if not href:
                continue
            if href.startswith('/'):
                href = urllib.parse.urljoin(base_url, href)
            if not href.startswith('http'):
                continue
            if href in visited:
                continue
            if _is_career_link(href, a.get_text()):
                links.append(href)
        return list(set(links))


ProviderRegistry.register(WebsiteCrawlerStrategy)
