from typing import AsyncIterator
from src.discovery.registry.source_registry import SourceRegistry
from src.discovery.models import RawJob, ConnectorCapability, Board
from src.discovery.registry.connector import Connector

class LeverConnector(Connector):
    @property
    def source_name(self) -> str:
        return "lever"
        

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
            normal_interval=300,
            priority=CrawlPriority.HIGH
        )
        
    async def sync(self, board: Board, http_client) -> AsyncIterator[RawJob]:
        api_url = f"https://api.lever.co/v0/postings/{board.identity.board_token}?mode=json"
        
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
            payload = result.payload
            if isinstance(payload, list):
                payload = {"jobs": payload}
            yield RawJob(provider="lever", board_identity=board.identity, payload=payload)

SourceRegistry.register(LeverConnector)

from src.discovery.registry.connector_registry import ConnectorRegistry
ConnectorRegistry.register('lever', LeverConnector)
