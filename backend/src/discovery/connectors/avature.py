import logging
import re
from urllib.parse import urlparse, urlunparse, parse_qs
from typing import AsyncIterator
from bs4 import BeautifulSoup
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("AvatureConnector")

_PSEUDO_TITLES = {
    "apply", "apply now", "apply online", "learn more", "view job",
    "view all", "see job", "more info", "details",
}


def _is_detail_href(href: str) -> bool:
    h = href.lower()
    return "/jobdetail" in h or "/projectdetail" in h or "/pipelinedetail" in h or "pipelineid=" in h


class AvatureConnector(Connector):
    """Avature connector — parses server-rendered HTML search page."""

    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="offset",
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
        base_url = self._resolve_base_url(board.endpoint)
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        page = 0
        page_size = 12
        seen = set()

        while True:
            offset = page * page_size
            url = f"{base_url}/careers/SearchJobs/?jobOffset={offset}&jobRecordsPerPage={page_size}"
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

            soup = BeautifulSoup(html_text, "html.parser")
            anchors = soup.find_all("a", href=lambda h: bool(h) and _is_detail_href(str(h)))

            if not anchors:
                break

            page_count = 0
            for anchor in anchors:
                href = anchor.get("href", "").strip()
                parsed_href = urlparse(href)
                query = parse_qs(parsed_href.query)
                ats_id = (query.get("pipelineId") or [""])[0]
                if not ats_id:
                    ats_id = href.rsplit("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
                if not ats_id or ats_id in seen:
                    continue
                seen.add(ats_id)
                page_count += 1

                # Locate wrapping container for title/location context
                container = anchor.find_parent(["article", "li", "tr"]) or anchor.find_parent(
                    "div",
                    class_=lambda v: bool(v) and any(
                        k in str(v).lower() for k in ("job", "result", "listing", "article")
                    ),
                )
                element = container or anchor

                # Extract Title
                title = ""
                title_el = element.find(["h2", "h3"]) or element.find(
                    class_=lambda v: bool(v) and "title" in str(v).lower()
                )
                if title_el:
                    title = title_el.get_text(strip=True)
                if not title:
                    anchor_text = anchor.get_text(strip=True)
                    if anchor_text.lower() not in _PSEUDO_TITLES:
                        title = anchor_text
                title = re.sub(r"\s+", " ", title).strip()
                if not title or title.lower() in _PSEUDO_TITLES:
                    continue

                # Location
                location = ""
                loc_el = element.find(class_=lambda v: bool(v) and "location" in str(v).lower())
                if loc_el:
                    location = re.sub(r"\s+", " ", loc_el.get_text(strip=True)).strip()

                # Department
                department = ""
                dept_el = element.find(
                    class_=lambda v: bool(v) and any(k in str(v).lower() for k in ("department", "category"))
                )
                if dept_el:
                    department = re.sub(r"\s+", " ", dept_el.get_text(strip=True)).strip()

                job_url = href if href.startswith("http") else f"{base_url.rstrip('/')}/{href.lstrip('/')}"

                payload = {
                    "id": ats_id,
                    "title": title,
                    "location": location,
                    "department": department,
                    "url": job_url,
                }

                yield RawJob(
                    company_id=board.company_id,
                    provider="avature",
                    board_identity=board.identity,
                    payload=payload,
                )

            if page_count == 0:
                break
            page += 1

        logger.info(f"AvatureConnector - Extracted {len(seen)} jobs across {page} pages.")

    def _resolve_base_url(self, endpoint: str) -> str:
        parsed = urlparse(endpoint)
        return f"{parsed.scheme}://{parsed.hostname}"


ConnectorRegistry.register("avature", "HTML", 10, AvatureConnector)
