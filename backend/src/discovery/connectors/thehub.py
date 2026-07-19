import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("TheHubConnector")


class TheHubConnector(Connector):
    """TheHub connector — uses the public JSON API at thehub.io/api/jobs."""

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
            supports_salary=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0 (compatible; CareerAutomated/1.0)"}
        page = 1
        max_pages = 20
        seen = set()

        while page <= max_pages:
            api_url = f"https://thehub.io/api/jobs?page={page}"
            result = await http_client.fetch("GET", api_url, headers=headers)

            if page == 1:
                should_sync = self.freshness_strategy().should_sync(board, result)
                yield result
                if not should_sync:
                    return

            if result.status_code != 200 or not isinstance(result.payload, dict):
                break

            items = result.payload.get("docs") or []
            if not items:
                break

            page_count = 0
            for item in items:
                if not isinstance(item, dict):
                    continue
                ats_id = str(item.get("id") or item.get("_id") or "")
                if not ats_id or ats_id in seen:
                    continue
                seen.add(ats_id)
                page_count += 1

                title = item.get("title") or ""
                if not title:
                    continue

                company = item.get("company") or {}
                company_name = company.get("name") if isinstance(company, dict) else str(company)

                location = item.get("location") or ""
                if isinstance(location, dict):
                    location = location.get("name") or location.get("city") or ""

                department = item.get("department") or ""

                payload = {
                    "id": ats_id,
                    "title": title,
                    "company": company_name or "",
                    "location": location,
                    "department": department,
                    "url": item.get("url") or item.get("apply_url") or "",
                    "created_at": item.get("published_at") or item.get("created_at") or "",
                }

                yield RawJob(
                    company_id=board.company_id,
                    provider="thehub",
                    board_identity=board.identity,
                    payload=payload,
                )

            if page_count == 0:
                break
            page += 1

        logger.info(f"TheHubConnector - Extracted {len(seen)} jobs across {page - 1} pages.")


ConnectorRegistry.register("thehub", "JSON", 10, TheHubConnector)
