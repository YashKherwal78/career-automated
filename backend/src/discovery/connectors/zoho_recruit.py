import logging
from typing import AsyncIterator

from src.discovery.models import RawJob, ConnectorCapability, Board
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("ZohoRecruitConnector")

class ZohoRecruitConnector(Connector):
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
        url = f"https://recruit.zoho.in/recruit/v2/public/OrgJobOpenings?digest={tenant}"
        headers = {"Accept": "application/json", "User-Agent": "CareerAutomated/1.0"}

        try:
            result = await http_client.fetch("GET", url, headers=headers)
            yield result

            if result.status_code == 200:
                payload = result.payload
                jobs = payload.get("data", []) if isinstance(payload, dict) else []
                for job in jobs:
                    if isinstance(job, dict):
                        yield RawJob(company_id=board.company_id, provider="zoho_recruit", board_identity=board.identity, payload=job)
        except Exception as e:
            logger.warning(f"ZohoRecruitConnector[{tenant}] sync failed: {e}")

ConnectorRegistry.register('zoho_recruit', 'JSON', 50, ZohoRecruitConnector)
