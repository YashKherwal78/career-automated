import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("BundesagenturConnector")


class BundesagenturConnector(Connector):
    """Bundesagentur für Arbeit connector — German federal employment search API."""

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
        api_url = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
        headers = {
            "X-API-Key": "jobboerse-jobsuche",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        }

        page = 1
        page_size = 100
        max_pages = 20  # Fetch the top 2000 freshest jobs per crawl cycle
        seen = set()

        while page <= max_pages:
            params = {
                "size": page_size,
                "page": page,
            }
            result = await http_client.fetch("GET", api_url, headers=headers, params=params)

            if page == 1:
                should_sync = self.freshness_strategy().should_sync(board, result)
                yield result
                if not should_sync:
                    return

            if result.status_code != 200 or not isinstance(result.payload, dict):
                break

            jobs = result.payload.get("stellenangebote") or []
            if not jobs:
                break

            page_count = 0
            for item in jobs:
                if not isinstance(item, dict):
                    continue
                ats_id = str(item.get("refnr") or "")
                if not ats_id or ats_id in seen:
                    continue
                seen.add(ats_id)
                page_count += 1

                title = item.get("titel") or ""
                if not title:
                    continue

                company = item.get("arbeitgeber") or ""
                
                # Location
                loc = item.get("arbeitsort") or {}
                location = ""
                if isinstance(loc, dict):
                    location = ", ".join(p for p in [loc.get("ort"), loc.get("land")] if p)
                elif isinstance(loc, str):
                    location = loc

                payload_item = {
                    "id": ats_id,
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": f"https://www.arbeitsagentur.de/jobsuche/jobdetails/{ats_id}",
                    "created_at": item.get("modifikationsTimestamp") or "",
                }

                yield RawJob(
                    company_id=board.company_id,
                    provider="bundesagentur",
                    board_identity=board.identity,
                    payload=payload_item,
                )

            if page_count == 0 or len(jobs) < page_size:
                break
            page += 1

        logger.info(f"BundesagenturConnector - Extracted {len(seen)} jobs.")


ConnectorRegistry.register("bundesagentur", "JSON", 10, BundesagenturConnector)
