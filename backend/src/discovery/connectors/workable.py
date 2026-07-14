import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("WorkableJSONConnector")

class WorkableJSONConnector(Connector):
    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="none",
            supports_etag=False,
            supports_last_modified=False,
            supports_content_hash=True,
            supports_incremental=False,
            supports_parallel_fetch=False,
            supports_snapshot=True,
            supports_bulk_fetch=True,
            supports_location=True,
            supports_departments=True,
            supports_remote=True
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()
        
    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        api_url = board.endpoint
        slug = getattr(board.identity, 'board_token', 'unknown')
        
        # We always want to fetch from the widget API
        if "api/v1/widget/accounts" not in api_url:
            api_url = f"https://apply.workable.com/api/v1/widget/accounts/{slug}"
            
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; jobhive/1.0)",
            "Accept": "application/json"
        }
        etag = board.metadata.get("etag")
        
        result = await http_client.fetch("GET", api_url, headers=headers, etag=etag)
        
        should_sync = self.freshness_strategy().should_sync(board, result)
        yield result
        
        if not should_sync:
            logger.info(f"WorkableJSONConnector[{slug}] - Content unchanged. Skipping sync.")
            return
            
        if result.status_code == 200 and isinstance(result.payload, dict):
            jobs = result.payload.get("jobs", [])
            for job in jobs:
                yield RawJob(provider="workable", board_identity=board.identity, payload=job)

ConnectorRegistry.register('workable', 'JSON', 100, WorkableJSONConnector)
