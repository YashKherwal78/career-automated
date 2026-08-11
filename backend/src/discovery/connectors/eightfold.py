import json
import logging
import re
from urllib.parse import urlparse
from typing import AsyncIterator
from bs4 import BeautifulSoup
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry
from src.discovery.html_text import strip_html

logger = logging.getLogger("EightfoldConnector")


class EightfoldConnector(Connector):
    """Eightfold connector — queries /api/pcsx/search with /api/apply/v2/jobs fallback."""

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
            supports_remote=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        domain = self._extract_domain(board.endpoint)
        base_url = self._resolve_base_url(board.endpoint)

        # 1. Try standard PCSX search first
        start = 0
        page_size = 10
        seen = set()

        url = f"{base_url}/api/pcsx/search"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0",
        }

        # Check if PCSX works
        params = {
            "domain": domain,
            "query": "",
            "location": "",
            "start": start,
            "sort_by": "timestamp",
        }
        
        result = await http_client.fetch("GET", url, headers=headers, params=params)

        if result.status_code == 403 or (
            result.status_code == 200 and isinstance(result.payload, dict) and 
            ("pcsx is not enabled" in str(result.payload.get("message", "")).lower())
        ):
            # Fallback to SmartApply endpoint
            logger.info(f"Eightfold - PCSX is not enabled/authorized for {domain}. Falling back to SmartApply.")
            url = f"{base_url}/api/apply/v2/jobs"

            while True:
                params = {
                    "domain": domain,
                    "query": "",
                    "location": "",
                    "start": start,
                    "sort_by": "timestamp",
                }
                result = await http_client.fetch("GET", url, headers=headers, params=params)

                if start == 0:
                    should_sync = self.freshness_strategy().should_sync(board, result)
                    yield result
                    if not should_sync:
                        return

                if result.status_code != 200 or not isinstance(result.payload, dict):
                    break

                positions = result.payload.get("positions") or []
                if not positions:
                    break

                page_count = 0
                for item in positions:
                    ats_id = str(item.get("id") or item.get("displayJobId") or "")
                    if not ats_id or ats_id in seen:
                        continue
                    seen.add(ats_id)
                    page_count += 1

                    yield RawJob(
                        company_id=board.company_id,
                        provider="eightfold",
                        board_identity=board.identity,
                        payload=await self._parse_item(item, base_url, http_client),
                    )

                if page_count == 0 or len(positions) < page_size:
                    break
                start += len(positions)
        else:
            # Continue with PCSX path
            while True:
                params = {
                    "domain": domain,
                    "query": "",
                    "location": "",
                    "start": start,
                    "sort_by": "timestamp",
                }
                if start > 0:
                    result = await http_client.fetch("GET", url, headers=headers, params=params)

                if start == 0:
                    should_sync = self.freshness_strategy().should_sync(board, result)
                    yield result
                    if not should_sync:
                        return

                if result.status_code != 200 or not isinstance(result.payload, dict):
                    break

                positions = result.payload.get("positions") or []
                if not positions:
                    break

                page_count = 0
                for item in positions:
                    ats_id = str(item.get("id") or item.get("displayJobId") or "")
                    if not ats_id or ats_id in seen:
                        continue
                    seen.add(ats_id)
                    page_count += 1

                    yield RawJob(
                        company_id=board.company_id,
                        provider="eightfold",
                        board_identity=board.identity,
                        payload=await self._parse_item(item, base_url, http_client),
                    )

                if page_count == 0 or len(positions) < page_size:
                    break
                start += len(positions)

        logger.info(f"EightfoldConnector[{domain}] - Extracted {len(seen)} jobs.")

    def _resolve_base_url(self, endpoint: str) -> str:
        parsed = urlparse(endpoint)
        return f"{parsed.scheme}://{parsed.hostname}"

    def _extract_domain(self, endpoint: str) -> str:
        parsed = urlparse(endpoint)
        hostname = parsed.hostname or ""
        # Often domain is query parameter or just hostname
        import urllib.parse
        queries = urllib.parse.parse_qs(parsed.query)
        if "domain" in queries:
            return queries["domain"][0]
        return hostname

    async def _parse_item(self, item: dict, base_url: str, http_client: HttpClient) -> dict:
        ats_id = str(item.get("id") or item.get("displayJobId") or "")

        # Location
        location = ""
        for key in ("standardizedLocations", "locations"):
            locs = item.get(key) or []
            if isinstance(locs, list) and locs:
                first = locs[0]
                if isinstance(first, str):
                    location = first
                elif isinstance(first, dict):
                    location = first.get("city") or first.get("country") or first.get("name") or ""
                if location:
                    break

        # Remote work options
        remote = ""
        for key in ("workLocationOption", "work_location_option", "locationFlexibility", "location_flexibility"):
            val = item.get(key)
            if isinstance(val, str) and val.strip():
                norm = val.lower()
                if "remote" in norm or "work from home" in norm or "wfh" in norm:
                    remote = "Remote"
                    break

        job_url = item.get("job_url") or item.get("canonicalPositionUrl") or f"{base_url}/careers/job/{ats_id}"

        # Search results ("positions") always report an empty job_description
        # field — verified live against mlp.eightfold.ai/api/apply/v2/jobs — so
        # a second per-job request against the detail page is required.
        description = await self._fetch_description(http_client, job_url, ats_id)

        return {
            "id": ats_id,
            "title": item.get("name") or item.get("posting_name") or item.get("title") or "",
            "location": location,
            "remote": remote,
            "department": item.get("department") or "",
            "employment_type": item.get("employmentType") or "",
            "url": job_url,
            "description": description,
        }

    async def _fetch_description(self, http_client: HttpClient, job_url: str, ats_id: str) -> str:
        """Fetch the job detail page and extract the JobPosting JSON-LD description."""
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            detail_result = await http_client.fetch("GET", job_url, headers=headers)
        except Exception as exc:
            logger.warning(f"EightfoldConnector - Detail fetch failed for job {ats_id}: {exc}")
            return ""

        if detail_result.status_code != 200:
            logger.warning(f"EightfoldConnector - Detail HTTP {detail_result.status_code} for job {ats_id}")
            return ""

        detail_html = detail_result.payload
        if isinstance(detail_html, bytes):
            detail_html = detail_html.decode("utf-8", errors="replace")
        if not isinstance(detail_html, str):
            return ""

        try:
            soup = BeautifulSoup(detail_html, "html.parser")
            for script in soup.find_all("script", type="application/ld+json"):
                if not script.string:
                    continue
                try:
                    data = json.loads(script.string)
                except (ValueError, TypeError):
                    continue
                if isinstance(data, dict) and data.get("@type") == "JobPosting":
                    return strip_html(data.get("description") or "")
            return ""
        except Exception as exc:
            logger.warning(f"EightfoldConnector - Failed to parse description for job {ats_id}: {exc}")
            return ""


ConnectorRegistry.register("eightfold", "JSON", 10, EightfoldConnector)
