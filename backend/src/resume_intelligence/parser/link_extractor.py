"""
Dedicated Link Extraction & URL Normalization Module.

Detects, extracts, validates, and normalizes candidate online profiles & URLs:
- GitHub, LinkedIn, Portfolio/Personal Website
- Medium, Dev.to, Twitter/X, Dribbble, Behance
- LeetCode, Codeforces, Kaggle, Google Scholar
"""

import re
from typing import Dict, Any, Optional
from pydantic import BaseModel


class ExtractedLinks(BaseModel):
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    website: Optional[str] = None
    medium: Optional[str] = None
    devto: Optional[str] = None
    twitter: Optional[str] = None
    dribbble: Optional[str] = None
    behance: Optional[str] = None
    leetcode: Optional[str] = None
    codeforces: Optional[str] = None
    kaggle: Optional[str] = None
    google_scholar: Optional[str] = None


class LinkExtractor:
    """Comprehensive Link Extraction and URL Normalizer."""

    URL_REGEX = re.compile(
        r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)',
        re.IGNORECASE
    )

    def extract_links(self, text: str) -> ExtractedLinks:
        found_urls = set(self.URL_REGEX.findall(text))
        links = ExtractedLinks()

        for url in found_urls:
            url_clean = url.rstrip('.,;) ]')
            u_lower = url_clean.lower()

            if "linkedin.com" in u_lower and not links.linkedin:
                links.linkedin = self._normalize_url(url_clean)
            elif "github.com" in u_lower and not links.github:
                links.github = self._normalize_url(url_clean)
            elif "medium.com" in u_lower and not links.medium:
                links.medium = self._normalize_url(url_clean)
            elif "dev.to" in u_lower and not links.devto:
                links.devto = self._normalize_url(url_clean)
            elif ("twitter.com" in u_lower or "x.com" in u_lower) and not links.twitter:
                links.twitter = self._normalize_url(url_clean)
            elif "dribbble.com" in u_lower and not links.dribbble:
                links.dribbble = self._normalize_url(url_clean)
            elif "behance.net" in u_lower and not links.behance:
                links.behance = self._normalize_url(url_clean)
            elif "leetcode.com" in u_lower and not links.leetcode:
                links.leetcode = self._normalize_url(url_clean)
            elif "codeforces.com" in u_lower and not links.codeforces:
                links.codeforces = self._normalize_url(url_clean)
            elif "kaggle.com" in u_lower and not links.kaggle:
                links.kaggle = self._normalize_url(url_clean)
            elif "scholar.google" in u_lower and not links.google_scholar:
                links.google_scholar = self._normalize_url(url_clean)
            elif not links.portfolio and not any(k in u_lower for k in ["linkedin", "github", "twitter", "x.com"]):
                links.portfolio = self._normalize_url(url_clean)

        return links

    def _normalize_url(self, url: str) -> str:
        if not url.startswith("http://") and not url.startswith("https://"):
            return f"https://{url}"
        return url
