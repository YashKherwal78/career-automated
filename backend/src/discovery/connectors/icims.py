import logging
import re
import html as html_lib
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("iCIMSConnector")

_JOB_CARD_RE = re.compile(
    r'<li[^>]+class="[^"]*iCIMS_JobCardItem[^"]*"[^>]*>(?P<body>.*?)</li>',
    re.DOTALL | re.IGNORECASE,
)
_JOB_ANCHOR_RE = re.compile(
    r'<a[^>]+href="(?P<href>https?://[^"]*?/jobs/(?P<id>\d+)/[^"]*?/job[^"]*)"[^>]*'
    r'class="[^"]*iCIMS_Anchor[^"]*"[^>]*>'
    r'(?P<inner>.*?)</a>',
    re.DOTALL | re.IGNORECASE,
)
_TITLE_RE = re.compile(r'<h3[^>]*>(?P<title>.*?)</h3>', re.DOTALL | re.IGNORECASE)
_LOCATION_RE = re.compile(
    r'<span[^>]+class="[^"]*sr-only[^"]*field-label[^"]*"[^>]*>\s*Job Locations\s*</span>'
    r'\s*<span[^>]*>\s*(?P<loc>[^<]*?)\s*</span>',
    re.DOTALL | re.IGNORECASE,
)
_HEADER_TAG_RE = re.compile(
    r'<dt[^>]*>(?P<label_html>.*?)</dt>'
    r'\s*<dd[^>]*>\s*<span[^>]*>(?P<value>.*?)</span>',
    re.DOTALL | re.IGNORECASE,
)
_DESC_RE = re.compile(
    r'<div[^>]+class="[^"]*col-xs-12[^"]*description[^"]*"[^>]*>(?P<desc>.*?)</div>',
    re.DOTALL | re.IGNORECASE,
)
_TAG_RE = re.compile(r"<[^>]+>")


def _strip(text: str) -> str:
    cleaned = _TAG_RE.sub(" ", text)
    cleaned = html_lib.unescape(cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


class iCIMSConnector(Connector):
    """iCIMS connector — paginates HTML search results."""

    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="page",
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
        base_url = self._resolve_base_url(board.endpoint)
        headers = {"User-Agent": "Mozilla/5.0"}
        
        page = 0
        max_pages = 50
        seen = set()

        while page < max_pages:
            url = f"{base_url}/jobs/search?ss=1&pr={page}&in_iframe=1"
            result = await http_client.fetch("GET", url, headers=headers)

            if page == 0:
                should_sync = self.freshness_strategy().should_sync(board, result)
                yield result
                if not should_sync:
                    return

            if result.status_code != 200:
                break

            html_text = result.payload
            if isinstance(html_text, bytes):
                html_text = html_text.decode("utf-8", errors="replace")
            if not isinstance(html_text, str):
                break

            page_count = 0
            for card in _JOB_CARD_RE.finditer(html_text):
                body = card.group("body")
                anchor = _JOB_ANCHOR_RE.search(body)
                if anchor is None:
                    continue
                ats_id = anchor.group("id")
                if ats_id in seen:
                    continue
                seen.add(ats_id)
                page_count += 1

                title_match = _TITLE_RE.search(anchor.group("inner"))
                title = _strip(title_match.group("title")) if title_match else ""
                if not title:
                    continue

                # Location
                location = ""
                loc_match = _LOCATION_RE.search(body)
                if loc_match:
                    location = _strip(loc_match.group("loc"))

                # Department
                department = ""
                for tag in _HEADER_TAG_RE.finditer(body):
                    if _strip(tag.group("label_html")).lower() == "category":
                        department = _strip(tag.group("value"))
                        break

                job_url = html_lib.unescape(anchor.group("href"))

                payload = {
                    "id": ats_id,
                    "title": title,
                    "location": location,
                    "department": department,
                    "url": job_url,
                }

                yield RawJob(
                    company_id=board.company_id,
                    provider="icims",
                    board_identity=board.identity,
                    payload=payload,
                )

            if page_count == 0:
                break
            page += 1

        logger.info(f"iCIMSConnector - Extracted {len(seen)} jobs across {page} pages.")

    def _resolve_base_url(self, endpoint: str) -> str:
        if endpoint.startswith(("http://", "https://")):
            return endpoint.rstrip("/")
        return f"https://careers-{endpoint}.icims.com"


ConnectorRegistry.register("icims", "HTML", 10, iCIMSConnector)
