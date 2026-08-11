import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry
from src.discovery.html_text import strip_html

logger = logging.getLogger("RipplingConnector")


class RipplingConnector(Connector):
    """Rippling connector — uses public API at api.rippling.com."""

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
        slug = self._extract_slug(board.endpoint)
        api_url = f"https://api.rippling.com/platform/api/ats/v1/board/{slug}/jobs"
        headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}

        result = await http_client.fetch("GET", api_url, headers=headers)
        should_sync = self.freshness_strategy().should_sync(board, result)
        yield result

        if not should_sync or result.status_code != 200 or not isinstance(result.payload, list):
            return

        seen = set()
        for job in result.payload:
            if not isinstance(job, dict):
                continue
            # Real response uses "uuid" as the identifier, not "id" — the old
            # code always read an empty string here, silently skipping every
            # job (verified against live data: api.rippling.com/.../jobs
            # returns real results, the connector just misread the shape).
            ats_id = str(job.get("uuid") or "")
            if not ats_id or ats_id in seen:
                continue
            seen.add(ats_id)

            # Real response uses "name" as the title field, not "title".
            title = job.get("name") or ""
            if not title:
                continue

            dept_obj = job.get("department") or {}
            department = dept_obj.get("label") or "" if isinstance(dept_obj, dict) else str(dept_obj)

            loc_obj = job.get("workLocation") or {}
            location = loc_obj.get("label") or "" if isinstance(loc_obj, dict) else str(loc_obj)

            # Check if there is an employment type dict
            emp_type_obj = job.get("employmentType") or {}
            emp_type = emp_type_obj.get("label") or "" if isinstance(emp_type_obj, dict) else str(emp_type_obj)

            job_url = job.get("url") or f"https://ats.rippling.com/{slug}/jobs/{ats_id}"

            description = await self._fetch_description(http_client, slug, ats_id)

            payload = {
                "id": ats_id,
                "title": title,
                "department": department,
                "location": location,
                "employment_type": emp_type,
                "url": job_url,
                "description": description,
            }

            yield RawJob(
                company_id=board.company_id,
                provider="rippling",
                board_identity=board.identity,
                payload=payload,
            )

        logger.info(f"RipplingConnector[{slug}] - Extracted {len(seen)} jobs.")

    async def _fetch_description(self, http_client: HttpClient, slug: str, ats_id: str) -> str:
        """Fetch the per-job API endpoint and extract the description.

        The board-level `/board/{slug}/jobs` list only has id/name/department/
        workLocation/url — verified against a live board (skillable-careers) —
        but the per-job endpoint at the same path plus the uuid returns a
        "description" object with "company" and "role" HTML fragments.
        """
        detail_url = f"https://api.rippling.com/platform/api/ats/v1/board/{slug}/jobs/{ats_id}"
        headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
        try:
            detail_result = await http_client.fetch("GET", detail_url, headers=headers)
        except Exception as exc:
            logger.warning(f"RipplingConnector[{slug}] - Detail fetch failed for job {ats_id}: {exc}")
            return ""

        if detail_result.status_code != 200 or not isinstance(detail_result.payload, dict):
            logger.warning(f"RipplingConnector[{slug}] - Detail HTTP {detail_result.status_code} for job {ats_id}")
            return ""

        try:
            desc_obj = detail_result.payload.get("description") or {}
            if isinstance(desc_obj, str):
                return strip_html(desc_obj)
            parts = [desc_obj.get("company") or "", desc_obj.get("role") or ""]
            combined = " ".join(p for p in parts if p)
            return strip_html(combined)
        except Exception as exc:
            logger.warning(f"RipplingConnector[{slug}] - Failed to parse description for job {ats_id}: {exc}")
            return ""

    def _extract_slug(self, endpoint: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(endpoint)
        path = parsed.path.strip("/")
        parts = path.split("/")
        if "board" in parts:
            idx = parts.index("board")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        if parts:
            if parts[-1] == "jobs" and len(parts) >= 2:
                return parts[-2]
            return parts[-1]
        return "unknown"




ConnectorRegistry.register("rippling", "JSON", 10, RipplingConnector)
