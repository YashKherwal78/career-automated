import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("ManfredConnector")


class ManfredConnector(Connector):
    """Manfred connector — uses the public JSON API at getmanfred.com/api/v2/public/offers."""

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
            supports_location=True,
            supports_remote=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        api_url = "https://www.getmanfred.com/api/v2/public/offers?lang=EN"
        headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0 (compatible; CareerAutomated/1.0)"}

        result = await http_client.fetch("GET", api_url, headers=headers)
        should_sync = self.freshness_strategy().should_sync(board, result)
        yield result

        if not should_sync or result.status_code != 200:
            return

        payload = result.payload
        if isinstance(payload, bytes):
            import json
            try:
                payload = json.loads(payload.decode("utf-8", errors="replace"))
            except Exception:
                payload = {}
        elif isinstance(payload, str):
            import json
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}

        items = []
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            items = payload.get("data") or payload.get("offers") or payload.get("results") or []

        seen = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            ats_id = str(item.get("id") or item.get("slug") or "")
            if not ats_id or ats_id in seen:
                continue
            seen.add(ats_id)

            title = item.get("title") or item.get("name") or ""
            if not title:
                continue

            company = item.get("company") or {}
            company_name = company.get("name") if isinstance(company, dict) else str(company or "")

            location = item.get("location") or item.get("city") or ""
            remote = "Remote" if item.get("remotePercentage", 0) == 100 else ""

            salary_min = item.get("salaryMin") or item.get("salary_min")
            salary_max = item.get("salaryMax") or item.get("salary_max")
            salary_currency = item.get("salaryCurrency") or item.get("salary_currency") or "EUR"

            payload = {
                "id": ats_id,
                "title": title,
                "company": company_name,
                "location": location,
                "remote": remote,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_currency": salary_currency,
                "url": item.get("url") or f"https://www.getmanfred.com/job-offers/{ats_id}",
                "created_at": item.get("publishedAt") or item.get("created_at") or "",
            }

            yield RawJob(
                company_id=board.company_id,
                provider="manfred",
                board_identity=board.identity,
                payload=payload,
            )

        logger.info(f"ManfredConnector - Extracted {len(seen)} jobs.")


ConnectorRegistry.register("manfred", "JSON", 10, ManfredConnector)
