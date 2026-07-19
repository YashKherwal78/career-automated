import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

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
            ats_id = str(job.get("id") or "")
            if not ats_id or ats_id in seen:
                continue
            seen.add(ats_id)

            title = job.get("title") or ""
            if not title:
                continue

            department = job.get("department") or ""
            location = job.get("workLocation") or ""

            # Check if there is an employment type dict
            emp_type_obj = job.get("employmentType") or {}
            emp_type = emp_type_obj.get("label") or "" if isinstance(emp_type_obj, dict) else str(emp_type_obj)

            payload = {
                "id": ats_id,
                "title": title,
                "department": department,
                "location": location,
                "employment_type": emp_type,
                "url": f"https://ats.rippling.com/board/{slug}/job/{ats_id}",
            }

            yield RawJob(
                company_id=board.company_id,
                provider="rippling",
                board_identity=board.identity,
                payload=payload,
            )

        logger.info(f"RipplingConnector[{slug}] - Extracted {len(seen)} jobs.")

    def _extract_slug(self, endpoint: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(endpoint)
        # Endpoint might look like https://ats.rippling.com/board/slug/jobs or similar
        path = parsed.path.strip("/")
        parts = path.split("/")
        if "board" in parts:
            idx = parts.index("board")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        return parts[-1] if parts else "unknown"


ConnectorRegistry.register("rippling", "JSON", 10, RipplingConnector)
