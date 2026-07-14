import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("LeverConnector")

class LeverConnector(Connector):
    
    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="none", # Lever usually returns all jobs or paginates with limit but we historically fetched all
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
        api_url = board.endpoint
        if "api.lever.co/v0/postings" not in api_url:
            company_id = board.identity.board_token if hasattr(board.identity, 'board_token') else 'unknown'
            api_url = f"https://api.lever.co/v0/postings/{company_id}?mode=json"
            
        headers = {"Accept": "application/json"}
        
        result = await http_client.fetch("GET", api_url, headers=headers)
        
        should_sync = self.freshness_strategy().should_sync(board, result)
        yield result
        
        if not should_sync:
            logger.info(f"LeverConnector[{getattr(board.identity, 'board_token', 'unknown')}] - Content unchanged. Skipping sync.")
            return
            
        if result.status_code == 200 and isinstance(result.payload, list):
            # Lever returns a direct list of jobs
            for job in result.payload:
                yield RawJob(provider="lever", company_id=board.company_id, board_identity=board.identity, payload=job)
        elif result.status_code == 200 and isinstance(result.payload, dict):
            # Just in case it returns {"data": [...]} in some versions
            job_list = result.payload.get("data", [])
            for job in job_list:
                yield RawJob(provider="lever", company_id=board.company_id, board_identity=board.identity, payload=job)

ConnectorRegistry.register('lever', 'HTML', 10, LeverConnector)

class LeverJSONConnector(LeverConnector):
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
            supports_remote=True
        )
    
ConnectorRegistry.register('lever', 'JSON', 100, LeverJSONConnector)
