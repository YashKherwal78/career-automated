import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("MercorConnector")


class MercorConnector(Connector):
    """Mercor connector — uses the public JSON API at aws.api.mercor.com."""

    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="none",
            supports_etag=False,
            supports_last_modified=False,
            supports_content_hash=True,
            supports_incremental=False,
            supports_parallel_fetch=False,
            supports_snapshot=True,
            supports_salary=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        api_url = "https://aws.api.mercor.com/work/listings-explore-page"
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; CareerAutomated/1.0)",
            "Authorization": "Bearer",
            "Origin": "https://work.mercor.com",
            "Referer": "https://work.mercor.com/",
        }

        result = await http_client.fetch("GET", api_url, headers=headers)
        should_sync = self.freshness_strategy().should_sync(board, result)
        yield result

        if not should_sync or result.status_code != 200:
            return

        payload = result.payload
        if isinstance(payload, bytes):
            import json
            try:
                payload = json.loads(payload.decode("utf-8"))
            except Exception:
                payload = {}
        elif not isinstance(payload, dict):
            payload = {}

        listings = payload.get("listings") or []
        seen = set()

        for listing in listings:
            if not isinstance(listing, dict):
                continue
            ats_id = str(listing.get("listingId") or "")
            if not ats_id or ats_id in seen:
                continue
            seen.add(ats_id)

            title = listing.get("title") or listing.get("name") or ""
            if not title:
                continue

            company = listing.get("company") or listing.get("company_name") or ""
            location = listing.get("location") or ""
            rate = listing.get("rate") or listing.get("compensation") or ""

            job_payload = {
                "id": ats_id,
                "title": title,
                "company": company,
                "location": location,
                "description": listing.get("description") or "",
                "rate": rate,
                "url": listing.get("url") or f"https://work.mercor.com/listings/{ats_id}",
                "created_at": listing.get("created_at") or "",
            }

            yield RawJob(
                company_id=board.company_id,
                provider="mercor",
                board_identity=board.identity,
                payload=job_payload,
            )

        logger.info(f"MercorConnector - Extracted {len(seen)} jobs.")


ConnectorRegistry.register("mercor", "JSON", 10, MercorConnector)
