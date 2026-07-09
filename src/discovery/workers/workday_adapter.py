from typing import AsyncIterator
import logging
from src.discovery.registry.source_registry import SourceRegistry
from src.discovery.models import RawJob, ConnectorCapability, Board
from src.discovery.registry.connector import Connector

logger = logging.getLogger("WorkdayConnector")

class WorkdayConnector(Connector):
    @property
    def source_name(self) -> str:
        return "workday"
        

    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="offset",
            supports_etag=False,
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
            normal_interval=900, # 15 minutes
            priority=CrawlPriority.LOW
        )
        
    async def sync(self, board: Board, http_client) -> AsyncIterator[RawJob]:
        api_url = board.endpoint
        if "/wday/cxs/" not in api_url:
            # Reconstruct api_url from identity if it's not the api_url
            domain = board.endpoint.split("://")[-1].split("/")[0]
            api_url = f"https://{domain}/wday/cxs/{board.identity.tenant}/{board.identity.site}/jobs"
            
        limit = 20
        offset = 0
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Check freshness on first page
        payload = {"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""}
        result = await http_client.fetch("POST", api_url, headers=headers, json=payload)
        
        if result.status_code == 304:
            return
            
        if not self.should_sync(board, result):
            return
            
        if result.content_hash:
            board.metadata["last_content_hash"] = result.content_hash
            
        # Process first page
        if result.status_code == 200 and isinstance(result.payload, dict):
            job_list = result.payload.get("jobPostings", [])
            for job in job_list:
                yield RawJob(provider="workday", board_identity=board.identity, payload=job)
                
            if len(job_list) < limit:
                return
                
            offset += limit
            
        # Paginate the rest
        while True:
            payload = {"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""}
            result = await http_client.fetch("POST", api_url, headers=headers, json=payload)
            
            if result.status_code != 200 or not isinstance(result.payload, dict):
                break
                
            job_list = result.payload.get("jobPostings", [])
            if not job_list:
                break
                
            for job in job_list:
                yield RawJob(provider="workday", board_identity=board.identity, payload=job)
                
            if len(job_list) < limit:
                break
                
            offset += limit

SourceRegistry.register(WorkdayConnector)
