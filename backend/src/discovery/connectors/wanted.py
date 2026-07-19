import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("WantedConnector")

class WantedConnector(Connector):
    """Wanted connector — uses the public REST API at wanted.co.kr/api/v4/jobs."""

    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="cursor",
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
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        # We start with the default API URL, or follow pagination link
        next_url = "https://www.wanted.co.kr/api/v4/jobs?country=kr&job_sort=job.latest_order&limit=100"
        seen = set()
        page = 1
        max_pages = 50  # Prevent infinite loops

        while next_url and page <= max_pages:
            result = await http_client.fetch("GET", next_url, headers=headers)
            
            if page == 1:
                should_sync = self.freshness_strategy().should_sync(board, result)
                yield result
                if not should_sync:
                    return
            
            if result.status_code != 200 or not isinstance(result.payload, dict):
                break

            jobs = result.payload.get("data") or []
            if not jobs:
                break

            for job in jobs:
                if not isinstance(job, dict):
                    continue
                ats_id = str(job.get("id") or "")
                if not ats_id or ats_id in seen:
                    continue
                seen.add(ats_id)

                title = job.get("position") or ""
                if not title:
                    continue

                company = job.get("company", {})
                company_name = company.get("name") if isinstance(company, dict) else str(company)

                address = job.get("address") or {}
                location = ""
                if isinstance(address, dict):
                    location = f"{address.get('country', '')} {address.get('location', '')}".strip()
                elif isinstance(address, str):
                    location = address

                payload = {
                    "id": ats_id,
                    "title": title,
                    "company": company_name,
                    "location": location,
                    "url": f"https://www.wanted.co.kr/wd/{ats_id}",
                    "created_at": job.get("published_at") or "",
                }

                yield RawJob(
                    company_id=board.company_id,
                    provider="wanted",
                    board_identity=board.identity,
                    payload=payload,
                )

            links = result.payload.get("links") or {}
            next_url = links.get("next")
            if next_url and not next_url.startswith("http"):
                next_url = f"https://www.wanted.co.kr{next_url}"
            page += 1

        logger.info(f"WantedConnector - Extracted {len(seen)} jobs across {page - 1} pages.")

ConnectorRegistry.register("wanted", "JSON", 10, WantedConnector)
