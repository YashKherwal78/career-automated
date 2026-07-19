import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("TikTokConnector")


class TikTokConnector(Connector):
    """TikTok careers connector — uses Life@TikTok search API."""

    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="offset",
            supports_etag=False,
            supports_last_modified=False,
            supports_content_hash=True,
            supports_incremental=False,
            supports_parallel_fetch=False,
            supports_snapshot=True,
            supports_location=True,
            supports_departments=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        headers = {
            "Accept": "*/*",
            "Content-Type": "application/json",
            "website-path": "tiktok",
            "Origin": "https://lifeattiktok.com",
            "Referer": "https://lifeattiktok.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        limit = 100
        offset = 0
        max_offset = 200
        seen = set()

        while offset <= max_offset:
            body = {
                "limit": limit,
                "offset": offset,
                "keyword": "",
                "category_id_list": [],
                "subject_id_list": [],
                "location_code_list": [],
                "job_function_id_list": [],
            }

            api_url = "https://api.lifeattiktok.com/api/v1/public/supplier/search/job/posts"
            result = await http_client.fetch("POST", api_url, headers=headers, json=body)

            if offset == 0:
                should_sync = self.freshness_strategy().should_sync(board, result)
                yield result
                if not should_sync:
                    return

            if result.status_code != 200 or not isinstance(result.payload, dict):
                break

            data = result.payload.get("data") or {}
            job_post_list = data.get("job_post_list") or []
            if not job_post_list:
                break

            page_count = 0
            for item in job_post_list:
                if not isinstance(item, dict):
                    continue
                ats_id = str(item.get("id") or "")
                if not ats_id or ats_id in seen:
                    continue
                seen.add(ats_id)
                page_count += 1

                title = item.get("title") or item.get("name") or "Untitled"
                
                # Department/Team
                category = item.get("job_category") or {}
                department = category.get("en_name") or category.get("name") or ""

                # Location
                city_info = item.get("city_info") or {}
                location = city_info.get("en_name") or city_info.get("name") or "Global"

                payload_item = {
                    "id": ats_id,
                    "title": title,
                    "company": "TikTok",
                    "department": department,
                    "location": location,
                    "url": f"https://lifeattiktok.com/search/{ats_id}",
                }

                yield RawJob(
                    company_id=board.company_id,
                    provider="tiktok",
                    board_identity=board.identity,
                    payload=payload_item,
                )

            if page_count == 0 or len(job_post_list) < limit:
                break
            offset += limit

        logger.info(f"TikTokConnector - Extracted {len(seen)} jobs.")


ConnectorRegistry.register("tiktok", "JSON", 10, TikTokConnector)
