import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("RecruiterboxConnector")

# Recruiterbox (Trakstar Hire) API endpoint
API_TEMPLATE = "https://jsapi.recruiterbox.com/v1/openings?client_name={slug}"


class RecruiterboxConnector(Connector):
    """Recruiterbox (Trakstar Hire) connector — public JSON API."""

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
            supports_remote=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        slug = self._extract_slug(board.endpoint)
        api_url = API_TEMPLATE.format(slug=slug)
        headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0 (compatible; CareerAutomated/1.0)"}

        result = await http_client.fetch("GET", api_url, headers=headers)
        should_sync = self.freshness_strategy().should_sync(board, result)
        yield result

        if not should_sync:
            return

        if result.status_code != 200:
            return

        payload = result.payload
        objects = []
        if isinstance(payload, dict):
            objects = payload.get("objects") or payload.get("results") or payload.get("data") or []
        elif isinstance(payload, list):
            objects = payload

        seen = set()
        for obj in objects:
            if not isinstance(obj, dict):
                continue
            ats_id = str(obj.get("id") or "")
            if not ats_id or ats_id in seen:
                continue
            seen.add(ats_id)

            title = obj.get("title") or ""
            if not title:
                continue

            # Location
            loc = obj.get("location") or {}
            location = ""
            if isinstance(loc, dict):
                parts = [loc.get("city"), loc.get("state"), loc.get("country")]
                location = ", ".join(p for p in parts if p)
            elif isinstance(loc, str):
                location = loc

            remote = "Remote" if obj.get("allows_remote") else ""
            department = obj.get("team") or ""
            emp_type = obj.get("position_type") or ""

            job_url = obj.get("hosted_url") or ""

            payload_item = {
                "id": ats_id,
                "title": title,
                "location": location,
                "remote": remote,
                "department": department,
                "employment_type": emp_type,
                "url": job_url,
            }

            yield RawJob(
                company_id=board.company_id,
                provider="recruiterbox",
                board_identity=board.identity,
                payload=payload_item,
            )

        logger.info(f"RecruiterboxConnector[{slug}] - Extracted {len(seen)} jobs.")

    def _extract_slug(self, endpoint: str) -> str:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(endpoint)
        # Try query param client_name
        qs = parse_qs(parsed.query)
        if "client_name" in qs:
            return qs["client_name"][0]
        hostname = parsed.hostname or ""
        if ".recruiterbox.com" in hostname or ".trakstar.com" in hostname:
            return hostname.split(".")[0]
        return hostname or "unknown"


ConnectorRegistry.register("recruiterbox", "JSON", 10, RecruiterboxConnector)
