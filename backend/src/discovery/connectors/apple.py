import logging
import json
from urllib.parse import urlparse
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("AppleConnector")


class AppleConnector(Connector):
    """Apple connector — uses public JSON search API with CSRF token."""

    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="page",
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
        base_url = "https://jobs.apple.com"
        csrf_url = f"{base_url}/api/v1/CSRFToken"
        search_url = f"{base_url}/api/v1/search"

        # 1. Fetch CSRF token
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Origin": base_url,
            "Referer": f"{base_url}/en-us/search",
        }
        
        csrf_res = await http_client.fetch("GET", csrf_url, headers=headers)
        if csrf_res.status_code != 200:
            logger.warning(f"Apple CSRF request failed {csrf_res.status_code}")
            yield csrf_res
            return

        csrf_token = (
            csrf_res.response_headers.get("x-apple-csrf-token") or
            csrf_res.response_headers.get("X-Apple-CSRF-Token") or
            csrf_res.response_headers.get("X-APPLE-CSRF-TOKEN")
        )
        if not csrf_token:
            logger.warning("Apple CSRF token not found in headers")
            yield csrf_res
            return

        headers["X-Apple-CSRF-Token"] = csrf_token

        page = 1
        page_size = 20
        seen = set()

        while True:
            payload = {
                "query": "",
                "filters": {},
                "page": page,
                "locale": "en-us",
                "sort": "",
                "format": {
                    "longDate": "MMMM D, YYYY",
                    "mediumDate": "MMM D, YYYY",
                },
            }
            result = await http_client.fetch("POST", search_url, headers=headers, json=payload)

            if page == 1:
                should_sync = self.freshness_strategy().should_sync(board, result)
                yield result
                if not should_sync:
                    return

            if result.status_code != 200 or not isinstance(result.payload, dict):
                break

            res_data = result.payload.get("res") or {}
            postings = res_data.get("searchResults") or []
            if not postings:
                break

            page_count = 0
            for item in postings:
                ats_id = str(item.get("reqId") or item.get("id") or "")
                if not ats_id or ats_id in seen:
                    continue
                seen.add(ats_id)
                page_count += 1

                title = item.get("postingTitle") or item.get("title") or ""
                if not title:
                    continue

                locations = item.get("locations") or []
                location = ""
                if locations and isinstance(locations, list):
                    first_loc = locations[0]
                    if isinstance(first_loc, dict):
                        location = first_loc.get("city") or first_loc.get("countryName") or ""

                team = item.get("team") or {}
                department = team.get("teamName") or "" if isinstance(team, dict) else str(team)

                payload_item = {
                    "id": ats_id,
                    "title": title,
                    "location": location,
                    "department": department,
                    "url": f"https://jobs.apple.com/en-us/details/{item.get('positionId') or ats_id}",
                    "description": item.get("jobSummary") or "",
                }

                yield RawJob(
                    company_id=board.company_id,
                    provider="apple",
                    board_identity=board.identity,
                    payload=payload_item,
                )

            total = res_data.get("totalRecords", 0)
            if page * page_size >= total or len(postings) < page_size or page_count == 0:
                break
            page += 1

        logger.info(f"AppleConnector - Extracted {len(seen)} jobs.")


ConnectorRegistry.register("apple", "JSON", 10, AppleConnector)
