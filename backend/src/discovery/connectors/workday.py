import logging
import asyncio
from typing import AsyncIterator, Optional
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.detail_fetch import DetailFetchThrottle, get_cached_description, cache_description
from src.discovery.html_text import strip_html

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

    async def _fetch_description(
        self, cxs_base: str, external_path: str, http_client: HttpClient, throttle: DetailFetchThrottle
    ) -> Optional[str]:
        """
        Workday's list endpoint (jobPostings) never includes the JD body —
        it lives behind a second GET to /wday/cxs/{tenant}/{site}{externalPath},
        where jobPostingInfo.jobDescription is the full HTML description.
        """
        if not external_path:
            return None

        cached = get_cached_description("workday", external_path)
        if cached is not None:
            return cached

        await throttle.wait()
        detail_url = f"{cxs_base}{external_path}"
        try:
            result = await http_client.fetch(
                "GET", detail_url, headers={"Accept": "application/json"}
            )
        except Exception as e:
            logger.debug("WorkdayConnector: detail fetch failed for %s: %s", external_path, e)
            return None

        if result.status_code != 200 or not isinstance(result.payload, dict):
            return None

        raw_desc = (
            result.payload.get("jobPostingInfo", {}).get("jobDescription", "")
            if isinstance(result.payload.get("jobPostingInfo"), dict)
            else ""
        )
        description = strip_html(raw_desc)
        cache_description("workday", external_path, description)
        return description

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        api_url = board.endpoint
        if "/wday/cxs/" not in api_url:
            domain = board.endpoint.split("://")[-1].split("/")[0]
            api_url = f"https://{domain}/wday/cxs/{board.identity.tenant}/{board.identity.site}/jobs"

        cxs_base = api_url.rsplit("/jobs", 1)[0]
        throttle = DetailFetchThrottle(requests_per_second=5.0)

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



        # Helper for batch detail fetching
        async def fetch_descriptions_for_batch(jobs):
            tasks = [
                self._fetch_description(cxs_base, job.get("externalPath", ""), http_client, throttle)
                for job in jobs
            ]
            descriptions = await asyncio.gather(*tasks, return_exceptions=True)
            for job, desc in zip(jobs, descriptions):
                job["description"] = desc if isinstance(desc, str) else ""

        # Process Page 1
        if result.status_code == 200 and isinstance(result.payload, dict):
            job_list = result.payload.get("jobPostings", [])
            await fetch_descriptions_for_batch(job_list)
            for job in job_list:
                yield RawJob(company_id=board.company_id, provider="workday", board_identity=board.identity, payload=job)

            if len(job_list) < limit:
                return

            offset += limit
        else:
            return

        # Paginate remaining pages (Capped at 5 pages / 100 jobs max per crawl cycle to maintain high system throughput)
        max_pages = 5
        page_count = 1

        while page_count < max_pages:
            payload = {"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""}
            try:
                result = await http_client.fetch("POST", api_url, headers=headers, json=payload)
            except Exception as e:
                logger.debug(f"Workday pagination fetch error: {e}")
                break

            yield result
            if result.status_code != 200 or not isinstance(result.payload, dict):
                break

            job_list = result.payload.get("jobPostings", [])
            if not job_list:
                break

            await fetch_descriptions_for_batch(job_list)
            for job in job_list:
                yield RawJob(company_id=board.company_id, provider="workday", board_identity=board.identity, payload=job)

            if len(job_list) < limit:
                break

            offset += limit
            page_count += 1

from src.discovery.registry.connector_registry import ConnectorRegistry
ConnectorRegistry.register('workday', 'HTML', 10, WorkdayConnector)

class WorkdayJSONConnector(WorkdayConnector):
    pass

ConnectorRegistry.register('workday', 'JSON', 100, WorkdayJSONConnector)
