from typing import AsyncIterator
import logging
from src.discovery.models import RawJob, ConnectorCapability, Board
from src.discovery.registry.connector import Connector
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("SmartRecruitersConnector")

class SmartRecruitersConnector(Connector):
    @property
    def source_name(self) -> str:
        return "smartrecruiters"

    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="offset",
            supports_etag=True,
            supports_last_modified=False,
            supports_content_hash=True,
            supports_incremental=False,
            supports_parallel_fetch=False,
            supports_snapshot=True,
        )
        
    async def sync(self, board: Board, http_client) -> AsyncIterator[RawJob]:
        api_url = f"https://api.smartrecruiters.com/v1/companies/{board.identity.company_identifier}/postings"
        
        limit = 100
        offset = 0
        
        # Check freshness on first page
        etag = board.metadata.get("etag")
        
        first_page_url = f"{api_url}?limit={limit}&offset={offset}"
        result = await http_client.fetch("GET", first_page_url, etag=etag)
        
        if result.status_code == 304:
            return
            
        if not self.freshness_strategy().should_sync(board, result):
            return
            
        if result.etag:
            board.metadata["etag"] = result.etag
        if result.content_hash:
            board.metadata["last_content_hash"] = result.content_hash
            
        # Process first page
        if result.status_code == 200 and isinstance(result.payload, dict):
            content = result.payload.get("content", [])
            for job in content:
                yield RawJob(provider="smartrecruiters", board_identity=board.identity, payload=job)
                
            if len(content) < limit:
                return
                
            offset += limit
            
        # Paginate the rest
        while True:
            paginated_url = f"{api_url}?limit={limit}&offset={offset}"
            result = await http_client.fetch("GET", paginated_url)
            
            if result.status_code != 200 or not isinstance(result.payload, dict):
                break
                
            content = result.payload.get("content", [])
            if not content:
                break
                
            for job in content:
                yield RawJob(provider="smartrecruiters", board_identity=board.identity, payload=job)
                
            if len(content) < limit:
                break
                
            offset += limit

ConnectorRegistry.register('smartrecruiters', SmartRecruitersConnector)
