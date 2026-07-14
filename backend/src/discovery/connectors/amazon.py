import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("AmazonJSONConnector")

class AmazonJSONConnector(Connector):
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
            supports_remote=False
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()
        
    def health(self) -> str:
        return "Experimental"
        
    def fingerprint(self) -> dict:
        return {
            "schema": "hash:a1b2c3d4",
            "endpoint": "https://www.amazon.jobs/api/jobs",
            "response": "json_array_jobs"
        }
        
    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        api_url = "https://www.amazon.jobs/api/jobs"
        result = await http_client.fetch("GET", api_url)
        yield result
        
        if result.status_code == 200 and isinstance(result.payload, dict):
            for job in result.payload.get("jobs", []):
                yield RawJob(provider="amazon", board_identity=board.identity, payload=job)

ConnectorRegistry.register('amazon', 'JSON', 100, AmazonJSONConnector)
