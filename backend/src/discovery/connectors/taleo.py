import logging
import re
import html
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("TaleoConnector")

_JOB_LINK_RE = re.compile(
    r'<a[^>]+href="(?P<href>[^"]*viewRequisition[^"]*\brid=(?P<rid>\d+)[^"]*)"'
    r'[^>]*class="(?:[^"]*\s)?viewJobLink(?:\s[^"]*)?"[^>]*>'
    r'(?P<title>.*?)</a>',
    re.DOTALL | re.IGNORECASE,
)


class TaleoConnector(Connector):
    """Oracle Taleo Business Edition (TBE) connector."""

    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="none",
            supports_etag=False,
            supports_last_modified=False,
            supports_content_hash=True,
            supports_incremental=False,
            supports_parallel_fetch=False,
            supports_snapshot=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        # Taleo URL must be fully specified in endpoint (or board company_id if it's a URL)
        url = board.endpoint
        if not url.startswith(("http://", "https://")):
            url = board.company_id

        if not url.startswith(("http://", "https://")):
            logger.error(f"TaleoConnector - Invalid endpoint URL: {url}")
            return

        result = await http_client.fetch("GET", url, headers=headers)

        should_sync = self.freshness_strategy().should_sync(board, result)
        yield result
        if not should_sync:
            return

        if result.status_code != 200:
            return

        html_text = result.payload
        if isinstance(html_text, bytes):
            html_text = html_text.decode("utf-8", errors="replace")
        if not isinstance(html_text, str) or not html_text:
            return

        # Extract company name from domain or path
        company = "Taleo"
        match_org = re.search(r"org=([^&]+)", url)
        if match_org:
            company = match_org.group(1).upper()

        seen = set()
        count = 0
        for match in _JOB_LINK_RE.finditer(html_text):
            rid = match.group("rid")
            if rid in seen:
                continue
            seen.add(rid)

            href = html.unescape(match.group("href"))
            title = html.unescape(match.group("title")).strip()
            title = re.sub(r"<[^>]+>", "", title).strip()

            if not title:
                continue

            payload_item = {
                "id": rid,
                "title": title,
                "company": company,
                "url": href,
            }

            yield RawJob(
                company_id=board.company_id,
                provider="taleo",
                board_identity=board.identity,
                payload=payload_item,
            )
            count += 1

        logger.info(f"TaleoConnector - Extracted {count} jobs.")


ConnectorRegistry.register("taleo", "HTML", 10, TaleoConnector)
