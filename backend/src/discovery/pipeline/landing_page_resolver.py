"""
LandingPageResolver — Sprint C1B

Responsibility: Given a generic /careers page URL, crawl it and extract any
embedded ATS endpoint, then return the resolved ATS URL for the Inspector.

This decouples "find where careers links are" from "validate an ATS board exists",
keeping each inspector focused only on its ATS-specific API surface.
"""

from __future__ import annotations

import re
import time
import logging
from typing import Optional, List, Tuple
from urllib.parse import urlparse

logger = logging.getLogger("LandingPageResolver")

# ATS URL patterns to search for in the page HTML.
# Each entry is (ats_name, compiled_pattern)
_ATS_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("Greenhouse",      re.compile(r'https?://boards\.greenhouse\.io/([^\s\'"<>]+)', re.I)),
    ("Greenhouse",      re.compile(r'https?://api\.greenhouse\.io/v1/boards/([^\s\'"<>]+)', re.I)),
    ("Lever",           re.compile(r'https?://jobs\.lever\.co/([^\s\'"<>]+)', re.I)),
    ("Ashby",           re.compile(r'https?://jobs\.ashbyhq\.com/([^\s\'"<>]+)', re.I)),
    ("Workday",         re.compile(r'https?://[a-z0-9-]+\.myworkdayjobs\.com/([^\s\'"<>]+)', re.I)),
    ("Workable",        re.compile(r'https?://[a-z0-9-]+\.workable\.com/([^\s\'"<>]+)', re.I)),
    ("SmartRecruiters", re.compile(r'https?://jobs\.smartrecruiters\.com/([^\s\'"<>]+)', re.I)),
    ("Teamtailor",      re.compile(r'https?://[a-z0-9-]+\.teamtailor\.com/([^\s\'"<>]+)', re.I)),
    ("BreezyHR",        re.compile(r'https?://[a-z0-9-]+\.breezy\.hr/([^\s\'"<>]+)', re.I)),
    ("Recruitee",       re.compile(r'https?://[a-z0-9-]+\.recruitee\.com/([^\s\'"<>]+)', re.I)),
    ("iCIMS",           re.compile(r'https?://[a-z0-9-]+\.icims\.com/([^\s\'"<>]+)', re.I)),
    ("Jobvite",         re.compile(r'https?://[a-z0-9-]+\.jobvite\.com/([^\s\'"<>]+)', re.I)),
    ("Eightfold",       re.compile(r'https?://[a-z0-9-]+\.eightfold\.ai/([^\s\'"<>]+)', re.I)),
    ("BambooHR",        re.compile(r'https?://[a-z0-9-]+\.bamboohr\.com/([^\s\'"<>]+)', re.I)),
]


class ResolvedEndpoint:
    """Result of a LandingPageResolver.resolve() call."""

    __slots__ = ("original_url", "resolved_url", "ats_name", "confidence", "method", "latency_ms", "error")

    def __init__(
        self,
        original_url: str,
        resolved_url: Optional[str] = None,
        ats_name: Optional[str] = None,
        confidence: float = 0.0,
        method: str = "unknown",
        latency_ms: int = 0,
        error: Optional[str] = None,
    ):
        self.original_url = original_url
        self.resolved_url = resolved_url
        self.ats_name = ats_name
        self.confidence = confidence
        self.method = method
        self.latency_ms = latency_ms
        self.error = error

    @property
    def success(self) -> bool:
        return self.resolved_url is not None


class LandingPageResolver:
    """
    Resolves a generic careers page URL → ATS endpoint.

    Pipeline:
        URL → HEAD (follow redirects) → if redirect lands on ATS, done.
              ↓ else
              GET page HTML → regex scan for ATS patterns → return best match.
              ↓ else
              return None (orchestrator will skip inspection for this candidate).

    This keeps ATS inspectors clean: they only receive verified ATS URLs.
    """

    def __init__(self, http_client):
        """
        :param http_client: An async-compatible HTTP client with a `.fetch(method, url)` interface.
                            Expected to be the same HttpClient used by the orchestrator.
        """
        self.http = http_client

    async def resolve(self, url: str) -> ResolvedEndpoint:
        start = time.time()
        try:
            # Step 1: Follow redirects via HEAD
            res = await self.http.fetch("HEAD", url)
            latency_ms = int((time.time() - start) * 1000)

            if res and res.final_url and res.final_url != url:
                final = res.final_url
                ats_name = self._match_ats_url(final)
                if ats_name:
                    logger.debug("LandingPageResolver: %s → %s via redirect (%s)", url, final, ats_name)
                    return ResolvedEndpoint(
                        original_url=url,
                        resolved_url=final,
                        ats_name=ats_name,
                        confidence=0.95,
                        method="redirect",
                        latency_ms=latency_ms,
                    )

            # Step 2: Fetch full HTML and scan
            get_start = time.time()
            get_res = await self.http.fetch("GET", url)
            latency_ms = int((time.time() - start) * 1000)

            if get_res and get_res.payload:
                html = get_res.payload.decode("utf-8", errors="ignore")
                resolved_url, ats_name, confidence = self._extract_from_html(html, url)
                if resolved_url:
                    logger.debug(
                        "LandingPageResolver: %s → %s via DOM scan (%s, conf=%.2f)",
                        url, resolved_url, ats_name, confidence,
                    )
                    return ResolvedEndpoint(
                        original_url=url,
                        resolved_url=resolved_url,
                        ats_name=ats_name,
                        confidence=confidence,
                        method="dom_scan",
                        latency_ms=latency_ms,
                    )

            return ResolvedEndpoint(
                original_url=url,
                latency_ms=latency_ms,
                error="No ATS endpoint found after redirect + DOM scan",
            )

        except Exception as exc:
            latency_ms = int((time.time() - start) * 1000)
            logger.warning("LandingPageResolver error for %s: %s", url, exc)
            return ResolvedEndpoint(original_url=url, latency_ms=latency_ms, error=str(exc))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _match_ats_url(url: str) -> Optional[str]:
        """Return the ATS name if the URL itself is a recognized ATS endpoint."""
        try:
            host = urlparse(url).netloc.lower()
        except Exception:
            return None
        for ats_name, pattern in _ATS_PATTERNS:
            if pattern.search(url):
                return ats_name
        return None

    @staticmethod
    def _extract_from_html(html: str, source_url: str) -> Tuple[Optional[str], Optional[str], float]:
        """
        Scan full HTML for ATS URL patterns.
        Returns (resolved_url, ats_name, confidence).
        Confidence decreases from 0.90 (iframe/script src) → 0.85 (href) → 0.80 (raw text match).
        """
        from bs4 import BeautifulSoup

        # Layer 1: Parse structured tags first (highest fidelity)
        try:
            soup = BeautifulSoup(html, "html.parser")

            # iframes and script srcs are very reliable ATS embeds
            for tag in soup.find_all(["iframe", "script"]):
                src = tag.get("src", "")
                for ats_name, pattern in _ATS_PATTERNS:
                    m = pattern.search(src)
                    if m:
                        return m.group(0), ats_name, 0.90

            # href links
            for tag in soup.find_all("a"):
                href = tag.get("href", "")
                for ats_name, pattern in _ATS_PATTERNS:
                    m = pattern.search(href)
                    if m:
                        return m.group(0), ats_name, 0.85
        except Exception:
            pass  # Fall through to raw regex

        # Layer 2: Raw regex over full HTML body (lowest confidence)
        for ats_name, pattern in _ATS_PATTERNS:
            m = pattern.search(html)
            if m:
                return m.group(0), ats_name, 0.80

        return None, None, 0.0
