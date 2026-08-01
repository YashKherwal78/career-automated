import logging
from typing import AsyncIterator

from src.discovery.models import RawJob, ConnectorCapability, Board
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("KekaConnector")

class KekaConnector(Connector):
    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="none",
            supports_etag=False,
            supports_last_modified=False,
            supports_content_hash=True,
            supports_incremental=False,
            supports_parallel_fetch=False,
            supports_snapshot=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob]:
        tenant = board.company_id
        url = f"https://{tenant}.keka.com/careers/api/embed/jobs"
        headers = {"Accept": "application/json", "User-Agent": "CareerAutomated/1.0"}

        try:
            result = await http_client.fetch("GET", url, headers=headers)
            yield result

            if result.status_code == 200:
                payload = result.payload
                jobs = payload if isinstance(payload, list) else (payload.get("jobs", []) if isinstance(payload, dict) else [])
                for job in jobs:
                    if isinstance(job, dict):
                        yield RawJob(company_id=board.company_id, provider="keka", board_identity=board.identity, payload=job)
        except Exception as e:
            logger.warning(f"KekaConnector[{tenant}] sync failed: {e}")

ConnectorRegistry.register('keka', 'JSON', 50, KekaConnector)
