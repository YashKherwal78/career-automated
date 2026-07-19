import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("UberConnector")


class UberConnector(Connector):
    """Uber careers connector — uses Uber loadSearchJobsResults API."""

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
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-csrf-token": "x",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        page = 0
        limit = 100
        max_pages = 5
        seen = set()

        while page < max_pages:
            body = {
                "limit": limit,
                "page": page,
                "params": {
                    "department": [],
                    "lineOfBusinessName": [],
                    "location": [],
                    "programAndPlatform": [],
                    "team": [],
                },
            }

            api_url = "https://www.uber.com/api/loadSearchJobsResults"
            result = await http_client.fetch("POST", api_url, headers=headers, params={"localeCode": "en"}, json=body)

            if page == 0:
                should_sync = self.freshness_strategy().should_sync(board, result)
                yield result
                if not should_sync:
                    return

            if result.status_code != 200 or not isinstance(result.payload, dict):
                break

            data = result.payload.get("data") or {}
            results = data.get("results") or []
            if not results:
                break

            page_count = 0
            for item in results:
                if not isinstance(item, dict):
                    continue
                ats_id = str(item.get("id") or "")
                if not ats_id or ats_id in seen:
                    continue
                seen.add(ats_id)
                page_count += 1

                title = item.get("title") or "Untitled"
                
                # Department/Team
                department = item.get("department") or ""

                # Location
                all_locs = item.get("allLocations") or []
                first_loc = all_locs[0] if all_locs else (item.get("location") or {})
                location = "Global"
                if isinstance(first_loc, dict):
                    parts = [
                        first_loc.get("city"),
                        first_loc.get("region"),
                        first_loc.get("countryName") or first_loc.get("country"),
                    ]
                    location = ", ".join(p for p in parts if p) or "Global"

                payload_item = {
                    "id": ats_id,
                    "title": title,
                    "company": "Uber",
                    "department": department,
                    "location": location,
                    "url": f"https://www.uber.com/global/en/careers/list/{ats_id}/",
                }

                yield RawJob(
                    company_id=board.company_id,
                    provider="uber",
                    board_identity=board.identity,
                    payload=payload_item,
                )

            if page_count == 0 or len(results) < limit:
                break
            page += 1

        logger.info(f"UberConnector - Extracted {len(seen)} jobs.")


ConnectorRegistry.register("uber", "JSON", 10, UberConnector)
