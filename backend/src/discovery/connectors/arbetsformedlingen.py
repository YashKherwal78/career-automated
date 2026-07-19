import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("ArbetsformedlingenConnector")


class ArbetsformedlingenConnector(Connector):
    """Arbetsförmedlingen connector — Sweden's federal job search API."""

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
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
        
        # We start with basic pagination on the main search endpoint
        offset = 0
        limit = 100
        max_offset = 2000  # Cap pagination for standard execution cycles
        seen = set()

        while offset < max_offset:
            url = f"https://jobsearch.api.jobtechdev.se/search?limit={limit}&offset={offset}"
            result = await http_client.fetch("GET", url, headers=headers)

            if offset == 0:
                should_sync = self.freshness_strategy().should_sync(board, result)
                yield result
                if not should_sync:
                    return

            if result.status_code != 200 or not isinstance(result.payload, dict):
                break

            hits = result.payload.get("hits") or []
            if not hits:
                break

            page_count = 0
            for item in hits:
                if not isinstance(item, dict):
                    continue
                ats_id = str(item.get("id") or "")
                if not ats_id or ats_id in seen:
                    continue
                seen.add(ats_id)
                page_count += 1

                title = item.get("headline") or item.get("title") or ""
                if not title:
                    continue

                # Location
                loc = item.get("workplace_address") or {}
                location = ""
                if isinstance(loc, dict):
                    location = loc.get("municipality") or loc.get("region") or loc.get("country") or ""

                company_obj = item.get("employer") or {}
                company = company_obj.get("name") if isinstance(company_obj, dict) else str(company_obj)

                payload_item = {
                    "id": ats_id,
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": item.get("webpage_url") or f"https://arbetsformedlingen.se/platsbanken/annonser/{ats_id}",
                    "description": (item.get("description") or {}).get("text") or "",
                }

                yield RawJob(
                    company_id=board.company_id,
                    provider="arbetsformedlingen",
                    board_identity=board.identity,
                    payload=payload_item,
                )

            if page_count == 0 or len(hits) < limit:
                break
            offset += limit

        logger.info(f"ArbetsformedlingenConnector - Extracted {len(seen)} jobs.")


ConnectorRegistry.register("arbetsformedlingen", "JSON", 10, ArbetsformedlingenConnector)
