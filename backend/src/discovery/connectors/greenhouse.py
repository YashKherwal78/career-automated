import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("GreenhouseConnector")

class GreenhouseConnector(Connector):
    
    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="none",
            supports_etag=True,
            supports_last_modified=False,
            supports_content_hash=True,
            supports_incremental=False,
            supports_parallel_fetch=False,
            supports_snapshot=True,
        )
        
    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()
        
    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob]:
        api_url = board.endpoint
        if "boards-api.greenhouse.io" not in api_url:
            company_id = board.identity.board_token if hasattr(board.identity, 'board_token') else 'unknown'
            api_url = f"https://boards-api.greenhouse.io/v1/boards/{company_id}/jobs"
            
        headers = {"Accept": "application/json"}
        
        # Greenhouse supports ETag, so let's pass it if we have it
        etag = board.metadata.get("etag")
        
        result = await http_client.fetch("GET", api_url, headers=headers, etag=etag)
        
        should_sync = self.freshness_strategy().should_sync(board, result)
        yield result
        
        if not should_sync:
            logger.info(f"GreenhouseConnector[{getattr(board.identity, 'board_token', 'unknown')}] - Content unchanged. Skipping sync.")
            return
            
        if result.status_code == 200 and isinstance(result.payload, dict):
            job_list = result.payload.get("jobs", [])
            for job in job_list:
                yield RawJob(provider="greenhouse", board_identity=board.identity, payload=job)

ConnectorRegistry.register('greenhouse', GreenhouseConnector)
