from typing import AsyncIterator
from src.discovery.registry.source_registry import SourceRegistry
from src.discovery.models import RawJob, ConnectorCapability, Board
from src.discovery.registry.connector import Connector

class AshbyConnector(Connector):
    @property
    def source_name(self) -> str:
        return "ashby"
        

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

    def crawl_policy(self):
        from src.discovery.registry.connector import CrawlPolicy, CrawlPriority
        return CrawlPolicy(
            version="v1",
            normal_interval=180,
            priority=CrawlPriority.NORMAL
        )
        
    async def sync(self, board: Board, http_client) -> AsyncIterator[RawJob]:
        api_url = f"https://api.ashbyhq.com/posting-api/job-board/{board.identity.board_token}"
        
        etag = board.metadata.get("etag")
        
        result = await http_client.fetch("GET", api_url, etag=etag)
        
        if result.status_code == 304:
            return
            
        if not self.freshness_strategy().should_sync(board, result):
            return
            
        if result.etag:
            board.metadata["etag"] = result.etag
        if result.content_hash:
            board.metadata["last_content_hash"] = result.content_hash
            
        if result.status_code == 200:
            yield RawJob(provider="ashby", board_identity=board.identity, payload=result.payload)

SourceRegistry.register(AshbyConnector)

from src.discovery.registry.connector_registry import ConnectorRegistry
ConnectorRegistry.register('ashby', AshbyConnector)
