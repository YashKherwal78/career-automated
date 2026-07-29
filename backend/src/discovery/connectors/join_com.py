import json
import hashlib
import logging
from typing import AsyncIterator, Optional
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry
from src.discovery.connectors.shared import NextJsParser, ProviderProfile, ProviderFingerprint
from src.discovery.detail_fetch import DetailFetchThrottle, get_cached_description, cache_description
from src.discovery.html_text import strip_html

logger = logging.getLogger("JoinComConnector")

class JoinComConnector(Connector):
    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="offset",
            supports_etag=False,
            supports_last_modified=False,
            supports_content_hash=True,
            supports_incremental=False,
            supports_parallel_fetch=False,
            supports_snapshot=True,
            supports_bulk_fetch=False,
            supports_location=True,
            supports_departments=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def discover_profile(self, board: Board, http_client: HttpClient) -> ProviderProfile:
        base = board.endpoint.rstrip("/")
        # We target the default listing route
        url = f"{base}"
        res = await http_client.fetch("GET", url)
        
        build_id = None
        schema_hash = ""
        
        if res.status_code == 200 and res.payload:
            data, build_id = NextJsParser.extract_next_data(res.payload)
            if data:
                initial_state = data.get("props", {}).get("pageProps", {}).get("initialState", {})
                jobs_items = initial_state.get("jobs", {}).get("items", [])
                if jobs_items:
                    # Fingerprint schema based on sorted keys of first item
                    sorted_keys = sorted(list(jobs_items[0].keys()))
                    schema_hash = hashlib.md5("".join(sorted_keys).encode()).hexdigest()
        
        fingerprint = ProviderFingerprint(
            version="nextjs-initialstate-v1",
            parser_type="next_data_json",
            schema_hash=schema_hash,
            build_id=build_id
        )
        
        return ProviderProfile(
            provider="join_com",
            interface="nextjs",
            endpoint=url,
            fingerprint=fingerprint,
            capabilities=self.capabilities()
        )

    async def _fetch_description(
        self, company_id: str, id_param: str, http_client: HttpClient, throttle: DetailFetchThrottle
    ) -> Optional[str]:
        """
        The listing page's __NEXT_DATA__ items never carry the JD body — it
        lives on the per-job detail page, under initialState.job.description
        (verified against a live posting). Reuses the same NextJsParser
        already used for the listing page.
        """
        if not id_param:
            return None

        cached = get_cached_description("join_com", id_param)
        if cached is not None:
            return cached

        await throttle.wait()
        detail_url = f"https://join.com/companies/{company_id}/{id_param}"
        try:
            result = await http_client.fetch("GET", detail_url)
        except Exception as e:
            logger.debug("JoinComConnector: detail fetch failed for %s: %s", id_param, e)
            return None

        if result.status_code != 200 or not result.payload:
            return None

        data, _ = NextJsParser.extract_next_data(result.payload)
        if not data:
            return None

        job_detail = data.get("props", {}).get("pageProps", {}).get("initialState", {}).get("job", {})
        description = strip_html(job_detail.get("description", "") if isinstance(job_detail, dict) else "")
        cache_description("join_com", id_param, description)
        return description

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        # 1. Discover profile
        profile = await self.discover_profile(board, http_client)
        throttle = DetailFetchThrottle(requests_per_second=5.0)

        # 2. Iterate pages
        page = 1
        has_more = True
        
        while has_more:
            url = f"{profile.endpoint}?page={page}" if page > 1 else profile.endpoint
            res = await http_client.fetch("GET", url)
            yield res
            
            if res.status_code != 200 or not res.payload:
                break
                
            data, _ = NextJsParser.extract_next_data(res.payload)
            if not data:
                break
                
            initial_state = data.get("props", {}).get("pageProps", {}).get("initialState", {})
            jobs_store = initial_state.get("jobs", {})
            items = jobs_store.get("items", [])
            
            for item in items:
                item["description"] = await self._fetch_description(
                    board.company_id, item.get("idParam", ""), http_client, throttle
                ) or ""
                # Keep numeric ID as stability anchor
                yield RawJob(
                    company_id=board.company_id,
                    provider="join_com",
                    board_identity=board.identity,
                    payload=item
                )
                
            # Parse pagination state
            pagination = jobs_store.get("pagination", {})
            page_count = pagination.get("pageCount", 1)
            current_page = pagination.get("page", page)
            
            if current_page < page_count:
                page += 1
            else:
                has_more = False

ConnectorRegistry.register('join_com', 'JSON', 100, JoinComConnector)
