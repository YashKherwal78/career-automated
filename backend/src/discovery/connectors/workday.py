import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient

logger = logging.getLogger("WorkdayConnector")

class WorkdayConnector(Connector):
    
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
            normal_interval=900,  # 15 minutes
            priority=CrawlPriority.LOW
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()
        
    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        api_url = board.endpoint
        if "/wday/cxs/" not in api_url:
            domain = board.endpoint.split("://")[-1].split("/")[0]
            api_url = f"https://{domain}/wday/cxs/{board.identity.tenant}/{board.identity.site}/jobs"
            
        limit = 20
        offset = 0
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Page 1 fetch
        payload = {"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""}
        result = await http_client.fetch("POST", api_url, headers=headers, json=payload)
        
        # Evaluate freshness
        should_sync = self.freshness_strategy().should_sync(board, result)
        yield result
        
        if not should_sync:
            logger.info(f"WorkdayConnector[{getattr(board.identity, 'board_token', 'unknown')}] - Content unchanged. Skipping sync.")
            return
            

            
        # Process Page 1
        if result.status_code == 200 and isinstance(result.payload, dict):
            job_list = result.payload.get("jobPostings", [])
            for job in job_list:
                yield RawJob(provider="workday", board_identity=board.identity, payload=job)
                
            if len(job_list) < limit:
                return
                
            offset += limit
        else:
            return
            
        # Paginate the rest
        while True:
            payload = {"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""}
            result = await http_client.fetch("POST", api_url, headers=headers, json=payload)
            
            yield result
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

from src.discovery.registry.connector_registry import ConnectorRegistry
ConnectorRegistry.register('workday', WorkdayConnector)
