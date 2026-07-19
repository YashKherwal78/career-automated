import logging
import re
from typing import AsyncIterator
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("GoogleConnector")


class GoogleConnector(Connector):
    """Google careers connector — parses Google public careers board."""

    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="page",
            supports_etag=False,
            supports_last_modified=False,
            supports_content_hash=True,
            supports_incremental=False,
            supports_parallel_fetch=False,
            supports_snapshot=True,
            supports_location=True,
            supports_departments=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

        page = 1
        max_pages = 5
        seen = set()

        while page <= max_pages:
            url = "https://www.google.com/about/careers/applications/jobs/results"
            params = {"hl": "en_US"}
            if page > 1:
                params["page"] = page

            result = await http_client.fetch("GET", url, headers=headers, params=params)

            if page == 1:
                should_sync = self.freshness_strategy().should_sync(board, result)
                yield result
                if not should_sync:
                    return

            if result.status_code != 200:
                break

            html_text = result.payload
            if isinstance(html_text, bytes):
                html_text = html_text.decode("utf-8", errors="replace")
            if not isinstance(html_text, str) or not html_text:
                break

            soup = BeautifulSoup(html_text, "html.parser")
            anchors = soup.find_all("a", attrs={"aria-label": True, "href": True})
            if not anchors:
                break

            page_count = 0
            for anchor in anchors:
                aria = anchor["aria-label"]
                if not aria.startswith("Learn more about"):
                    continue
                href = anchor["href"]
                job_url = urljoin("https://www.google.com/about/careers/applications/", href)
                
                # Extract ID from URL
                match = re.search(r"jobs/results/(\d+)", job_url)
                ats_id = match.group(1) if match else None
                if not ats_id or ats_id in seen:
                    continue
                seen.add(ats_id)
                page_count += 1

                title = aria.replace("Learn more about", "").strip()

                payload_item = {
                    "id": ats_id,
                    "title": title,
                    "company": "Google",
                    "url": job_url,
                }

                # Parse location from page text or sub-nodes if visible, but standard details live in details fetch.
                # For basic listing, we yield the raw job immediately.
                yield RawJob(
                    company_id=board.company_id,
                    provider="google",
                    board_identity=board.identity,
                    payload=payload_item,
                )

            if page_count == 0:
                break
            page += 1

        logger.info(f"GoogleConnector - Extracted {len(seen)} jobs across {page - 1} pages.")


ConnectorRegistry.register("google", "HTML", 10, GoogleConnector)
