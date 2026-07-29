import logging
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from src.discovery.seed_sources.base import SeedSource
from src.discovery.search.provider_manager import SearchManager

logger = logging.getLogger("SearchSource")

# For "site:{ats}" queries, every result IS on the ATS's own domain by
# design — the previous code discarded every single hit by filtering those
# domains out, so this source silently produced zero seeds ever. The ATS
# board URL itself is a perfectly good "website" seed (it self-verifies
# trivially against the known ATS signature), so we extract the company
# slug from the URL path instead of trying to find a root domain that was
# never going to be in these search results.
_ATS_SLUG_PATTERNS = {
    "greenhouse.io": re.compile(r"greenhouse\.io/(?:embed/job_board\?for=)?([a-zA-Z0-9_-]+)"),
    "lever.co": re.compile(r"lever\.co/([a-zA-Z0-9_-]+)"),
    "ashbyhq.com": re.compile(r"ashbyhq\.com/([a-zA-Z0-9_-]+)"),
}

_TITLE_COMPANY_RE = re.compile(r"(?:jobs at|job application for .* at)\s+(.+)$", re.IGNORECASE)


class SearchSource(SeedSource):
    name = "search"
    priority = 2
    enabled = True

    def __init__(self):
        self.search_manager = SearchManager()

    def _extract_slug(self, url: str) -> Optional[str]:
        for domain, pattern in _ATS_SLUG_PATTERNS.items():
            if domain in url:
                match = pattern.search(url)
                if match:
                    return match.group(1).lower()
        return None

    def _extract_company_name(self, title: str, fallback_slug: str) -> str:
        match = _TITLE_COMPANY_RE.search(title)
        if match:
            name = match.group(1).strip()
            if 0 < len(name) <= 40:
                return name
        return fallback_slug.replace("-", " ").title()

    async def discover(self) -> List[Dict[str, Any]]:
        logger.info("Discovering company seeds from SearchSource fallback...")

        # (query, country) — country is None for general queries, and set
        # for queries explicitly targeting Indian cities/companies so
        # discovered seeds carry real geography instead of nothing at all.
        queries = [
            ("site:greenhouse.io tech startup jobs", None),
            ("site:lever.co software engineer remote jobs", None),
            ("site:ashbyhq.com software engineer jobs", None),
            # India-specific — this product's candidate base is India-heavy
            # while job/company coverage is currently thin there (~2% of
            # active jobs), so these are weighted in explicitly rather than
            # left to chance.
            ("site:greenhouse.io Bangalore India jobs", "India"),
            ("site:lever.co Bangalore India jobs", "India"),
            ("site:ashbyhq.com India jobs", "India"),
            ("site:greenhouse.io Hyderabad OR Pune OR Gurgaon jobs", "India"),
        ]

        seen_slugs = set()
        discovered_seeds = []
        for q, country in queries:
            try:
                results = await self.search_manager.execute_search(q, limit=10)
                for r in results:
                    slug = self._extract_slug(r.url)
                    if not slug or slug in seen_slugs:
                        continue
                    seen_slugs.add(slug)

                    parsed = urlparse(r.url)
                    board_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    name = self._extract_company_name(r.title, slug)

                    seed = {
                        "company_id": slug,
                        "name": name,
                        "website": board_url,
                        "source": "search",
                        "confidence": 0.7,
                    }
                    if country:
                        seed["country"] = country
                    discovered_seeds.append(seed)
            except Exception as e:
                logger.error(f"SearchSource query '{q}' failed: {e}")

        return discovered_seeds
