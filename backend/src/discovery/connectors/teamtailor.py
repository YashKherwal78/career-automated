import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("TeamtailorJSONConnector")

class TeamtailorJSONConnector(Connector):
    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="offset",
            supports_etag=False,
            supports_last_modified=False,
            supports_content_hash=True,
            supports_incremental=False,
            supports_parallel_fetch=False,
            supports_snapshot=True,
            supports_bulk_fetch=True,
            supports_location=True,
            supports_departments=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()
        
    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        api_url = f"{board.endpoint}/api/v1/jobs"
        result = await http_client.fetch("GET", api_url)
        yield result
        if result.status_code == 200 and isinstance(result.payload, dict):
            for job in result.payload.get("data", []):
                yield RawJob(provider="teamtailor", board_identity=board.identity, payload=job)

ConnectorRegistry.register('teamtailor', 'JSON', 100, TeamtailorJSONConnector)
