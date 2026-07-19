import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("RemoteOKConnector")


class RemoteOKConnector(Connector):
    """RemoteOK connector — uses the public JSON API at /api."""

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
            supports_salary=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        api_url = "https://remoteok.com/api"
        headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0 (compatible; CareerAutomated/1.0)"}

        result = await http_client.fetch("GET", api_url, headers=headers)
        should_sync = self.freshness_strategy().should_sync(board, result)
        yield result

        if not should_sync:
            return

        if result.status_code != 200:
            return

        # RemoteOK API returns a JSON array where [0] is metadata
        items = result.payload if isinstance(result.payload, list) else []
        seen = set()

        for item in items:
            if not isinstance(item, dict):
                continue
            ats_id = str(item.get("id") or "")
            if not ats_id or ats_id in seen:
                continue
            # Skip the metadata/legal entry (first item)
            if "legal" in item and not item.get("position"):
                continue
            seen.add(ats_id)

            title = item.get("position") or ""
            if not title:
                continue

            company = item.get("company") or ""
            location = item.get("location") or "Remote"
            tags = item.get("tags") or []

            salary_min = item.get("salary_min")
            salary_max = item.get("salary_max")

            job_url = item.get("url") or f"https://remoteok.com/remote-jobs/{ats_id}"

            payload = {
                "id": ats_id,
                "title": title,
                "company": company,
                "location": location,
                "remote": "Remote",
                "tags": tags,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "url": job_url,
                "created_at": item.get("date") or "",
            }

            yield RawJob(
                company_id=board.company_id,
                provider="remoteok",
                board_identity=board.identity,
                payload=payload,
            )

        logger.info(f"RemoteOKConnector - Extracted {len(seen)} jobs.")


ConnectorRegistry.register("remoteok", "JSON", 10, RemoteOKConnector)
