import logging
import re
from urllib.parse import urlparse
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("CornerstoneConnector")

_TOKEN_RE = re.compile(r'csod\.context\.token\s*=\s*[\'"]([^\'"]+)[\'"]')
_TOKEN_FALLBACK_RE = re.compile(r'"token"\s*:\s*"([^"]+)"')
_API_HOST_RE = re.compile(r'(https?://[a-z0-9-]+\.api\.csod\.com)')
_DEFAULT_API_HOST = "https://na.api.csod.com"


class CornerstoneConnector(Connector):
    """Cornerstone connector — gets JWT and posts search query."""

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
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        career_url, slug, site_id = self._resolve_career_url(board.endpoint)

        # 1. Fetch home page to extract JWT token and api host
        init_res = await http_client.fetch("GET", career_url, headers={"User-Agent": "Mozilla/5.0"})
        if init_res.status_code != 200:
            logger.warning(f"CornerstoneConnector - Init request failed {init_res.status_code}")
            yield init_res
            return

        text = init_res.payload
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="replace")
        if not isinstance(text, str):
            yield init_res
            return

        match = _TOKEN_RE.search(text) or _TOKEN_FALLBACK_RE.search(text)
        if not match:
            logger.warning("CornerstoneConnector - Could not parse token")
            yield init_res
            return

        token = match.group(1)
        host_match = _API_HOST_RE.search(text)
        api_host = host_match.group(1) if host_match else _DEFAULT_API_HOST

        # 2. Query external/jobs endpoint
        url = f"{api_host}/rec-job-search/external/jobs"
        career_origin = f"https://{urlparse(career_url).hostname}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": career_origin,
            "Referer": career_origin + "/",
            "User-Agent": "Mozilla/5.0",
        }

        page = 1
        page_size = 25
        seen = set()

        while True:
            body = {
                "careerSiteId": site_id,
                "careerSitePageId": site_id,
                "pageNumber": page,
                "pageSize": page_size,
                "cultureId": 1,
                "cultureName": "en-US",
            }
            result = await http_client.fetch("POST", url, headers=headers, json=body)
            
            if page == 1:
                # Use first page search payload for content-hash freshness checks
                should_sync = self.freshness_strategy().should_sync(board, result)
                yield result
                if not should_sync:
                    return

            if result.status_code != 200 or not isinstance(result.payload, dict):
                break

            data = result.payload.get("data") or {}
            requisitions = data.get("requisitions") or []
            if not requisitions:
                break

            page_count = 0
            for item in requisitions:
                ats_id = str(item.get("requisitionId") or "")
                if not ats_id or ats_id in seen:
                    continue
                seen.add(ats_id)
                page_count += 1

                title = (item.get("displayJobTitle") or "").strip()
                if not title:
                    continue

                # Locations formatting
                loc_list = item.get("locations") or []
                location = ""
                if loc_list and isinstance(loc_list, list):
                    first_loc = loc_list[0]
                    if isinstance(first_loc, dict):
                        parts = [first_loc.get(k) for k in ("city", "state", "country") if first_loc.get(k)]
                        location = ", ".join(parts)

                job_url = f"{career_origin}/ux/ats/careersite/{site_id}/job/{ats_id}?c={slug}"

                payload_item = {
                    "id": ats_id,
                    "title": title,
                    "location": location,
                    "url": job_url,
                    "description": item.get("externalDescription") or "",
                }

                yield RawJob(
                    company_id=board.company_id,
                    provider="cornerstone",
                    board_identity=board.identity,
                    payload=payload_item,
                )

            if page_count == 0 or len(requisitions) < page_size:
                break
            page += 1

        logger.info(f"CornerstoneConnector[{slug}] - Extracted {len(seen)} jobs.")

    def _resolve_career_url(self, endpoint: str) -> tuple[str, str, int]:
        parsed = urlparse(endpoint)
        query = parsed.query
        # Extract c parameter (slug)
        slug = "unknown"
        m = re.search(r"[?&]c=([^&#]+)", endpoint)
        if m:
            slug = m.group(1)
        else:
            host = parsed.hostname or ""
            slug = host.split(".")[0] if host else slug
        
        site_match = re.search(r"/careersite/(\d+)/", endpoint)
        site_id = int(site_match.group(1)) if site_match else 1
        return endpoint, slug, site_id


ConnectorRegistry.register("cornerstone", "JSON", 10, CornerstoneConnector)
