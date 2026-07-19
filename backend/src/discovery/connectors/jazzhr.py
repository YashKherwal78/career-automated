import logging
import re
import html as html_lib
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("JazzHRConnector")

# Regex patterns ported from the reference JazzHR scraper
_ROW_RE = re.compile(
    r'<tr\s+id="row_job_[^"]+?"[^>]*>(?P<body>.*?)</tr>',
    re.DOTALL | re.IGNORECASE,
)
_TITLE_RE = re.compile(
    r'<a[^>]+class="[^"]*job_title_link[^"]*"[^>]+'
    r'href="/apply/jobs/details/(?P<id>[A-Za-z0-9_-]+)[^"]*"[^>]*>'
    r'(?P<title>.*?)</a>',
    re.DOTALL | re.IGNORECASE,
)
_DEPT_RE = re.compile(
    r'<span[^>]*class="[^"]*resumator_department[^"]*"[^>]*>'
    r'(?P<dept>.*?)</span>',
    re.DOTALL | re.IGNORECASE,
)
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(text: str) -> str:
    text = _TAG_RE.sub(" ", text)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


class JazzHRConnector(Connector):

    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="none",
            supports_etag=False,
            supports_last_modified=False,
            supports_content_hash=True,
            supports_incremental=False,
            supports_parallel_fetch=False,
            supports_snapshot=True,
            supports_departments=True,
            supports_location=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        # Resolve endpoint: extract slug from applytojob.com hostname
        endpoint = board.endpoint
        slug = self._extract_slug(endpoint)
        listing_url = f"https://{slug}.applytojob.com/apply/jobs"

        headers = {
            "Accept": "text/html",
            "User-Agent": "Mozilla/5.0 (compatible; CareerAutomated/1.0)"
        }

        result = await http_client.fetch("GET", listing_url, headers=headers)

        should_sync = self.freshness_strategy().should_sync(board, result)
        yield result

        if not should_sync:
            logger.info(f"JazzHRConnector[{slug}] - Content unchanged. Skipping sync.")
            return

        if result.status_code != 200:
            logger.warning(f"JazzHRConnector[{slug}] - HTTP {result.status_code}")
            return

        # Parse the HTML payload
        html_text = result.payload
        if isinstance(html_text, bytes):
            html_text = html_text.decode("utf-8", errors="replace")
        if not isinstance(html_text, str):
            logger.warning(f"JazzHRConnector[{slug}] - Unexpected payload type: {type(html_text)}")
            return

        seen = set()
        for row_match in _ROW_RE.finditer(html_text):
            body = row_match.group("body")
            title_match = _TITLE_RE.search(body)
            if not title_match:
                continue

            ats_id = title_match.group("id")
            if ats_id in seen:
                continue
            seen.add(ats_id)

            title = _strip_tags(title_match.group("title"))
            if not title:
                continue

            # Department
            dept_match = _DEPT_RE.search(body)
            department = _strip_tags(dept_match.group("dept")) if dept_match else ""

            # Location: second <td> in the row
            location = self._extract_location(body)

            job_url = f"https://{slug}.applytojob.com/apply/jobs/details/{ats_id}"

            payload = {
                "id": ats_id,
                "title": title,
                "department": department,
                "location": location,
                "url": job_url,
            }

            yield RawJob(
                company_id=board.company_id,
                provider="jazzhr",
                board_identity=board.identity,
                payload=payload,
            )

        logger.info(f"JazzHRConnector[{slug}] - Extracted {len(seen)} jobs.")

    def _extract_slug(self, endpoint: str) -> str:
        """Extract the tenant subdomain slug from an applytojob.com URL."""
        from urllib.parse import urlparse
        parsed = urlparse(endpoint)
        hostname = parsed.hostname or ""
        if ".applytojob.com" in hostname:
            return hostname.split(".applytojob.com")[0]
        # Fallback: use the path or the whole endpoint as slug
        return hostname or "unknown"

    def _extract_location(self, row_body: str) -> str:
        """Location is the text content of the last <td> in the row."""
        tds = re.findall(r"<td[^>]*>(.*?)</td>", row_body, re.DOTALL | re.IGNORECASE)
        if len(tds) < 2:
            return ""
        location = _strip_tags(tds[-1])
        return location or ""


ConnectorRegistry.register("jazzhr", "HTML", 10, JazzHRConnector)
