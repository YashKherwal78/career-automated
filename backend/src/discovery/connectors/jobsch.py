import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("JobsChConnector")


class JobsChConnector(Connector):
    """jobs.ch connector — Switzerland's largest job search engine."""

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
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        # Query parameter: we can fetch by a keyword, or fetch the general list
        query = board.company_id if not board.company_id.startswith("test-") else None

        start = 0
        rows = 20
        max_offset = 200
        seen = set()

        while start <= max_offset:
            params = {"rows": rows, "start": start}
            if query:
                params["query"] = query

            api_url = "https://www.jobs.ch/api/v1/public/search"
            result = await http_client.fetch("GET", api_url, headers=headers, params=params)

            if start == 0:
                should_sync = self.freshness_strategy().should_sync(board, result)
                yield result
                if not should_sync:
                    return

            if result.status_code != 200 or not isinstance(result.payload, dict):
                break

            documents = result.payload.get("documents") or []
            if not documents:
                break

            page_count = 0
            for doc in documents:
                if not isinstance(doc, dict):
                    continue
                ats_id = str(doc.get("job_id") or "")
                if not ats_id or ats_id in seen:
                    continue
                seen.add(ats_id)
                page_count += 1

                title = (doc.get("title") or "").strip()
                company = (doc.get("company_name") or "Unknown").strip()
                place = (doc.get("place") or "").strip()
                location = f"{place}, Switzerland" if place else "Switzerland"

                # Construct detail link
                links = doc.get("_links") or {}
                detail_url = ""
                if isinstance(links, dict):
                    detail_de = links.get("detail_de") or {}
                    if isinstance(detail_de, dict):
                        detail_url = detail_de.get("href") or ""
                if not detail_url:
                    detail_url = f"https://www.jobs.ch/en/jobs/detail/{ats_id}"

                payload_item = {
                    "id": ats_id,
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": detail_url,
                }

                yield RawJob(
                    company_id=board.company_id,
                    provider="jobsch",
                    board_identity=board.identity,
                    payload=payload_item,
                )

            if page_count == 0 or len(documents) < rows:
                break
            start += rows

        logger.info(f"JobsChConnector - Extracted {len(seen)} jobs.")


ConnectorRegistry.register("jobsch", "JSON", 10, JobsChConnector)
