import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("GemConnector")

class GemConnector(Connector):
    """Gem connector — uses public GraphQL API to fetch listings."""

    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="none",
            supports_etag=False,
            supports_last_modified=False,
            supports_content_hash=True,
            supports_incremental=False,
            supports_parallel_fetch=False,
            supports_snapshot=True,
            supports_graphql=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        slug = self._extract_slug(board.endpoint)
        api_url = "https://jobs.gem.com/api/public/graphql/batch"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }

        # Query to fetch all active job postings on the board
        query = """
        query JobBoardList($boardId: String!) {
            jobBoard(id: $boardId) {
                name
                jobPostings {
                    id
                    title
                    locations {
                        city
                        state
                        country
                    }
                    department {
                        name
                    }
                    employmentType
                }
            }
        }
        """

        payload = [{"operationName": "JobBoardList", "query": query, "variables": {"boardId": slug}}]
        result = await http_client.fetch("POST", api_url, headers=headers, json=payload)
        should_sync = self.freshness_strategy().should_sync(board, result)
        yield result

        if not should_sync:
            return

        if result.status_code != 200 or not isinstance(result.payload, list):
            return

        # GraphQL batch responds with an array of responses
        response_data = result.payload[0] if len(result.payload) > 0 else {}
        job_board = response_data.get("data", {}).get("jobBoard") or {}
        postings = job_board.get("jobPostings") or []

        seen = set()
        for post in postings:
            if not isinstance(post, dict):
                continue
            ats_id = str(post.get("id") or "")
            if not ats_id or ats_id in seen:
                continue
            seen.add(ats_id)

            title = post.get("title") or ""
            if not title:
                continue

            locations = post.get("locations") or []
            location = ""
            if isinstance(locations, list) and len(locations) > 0:
                loc_list = []
                for loc in locations:
                    if isinstance(loc, dict):
                        parts = [loc.get("city"), loc.get("state"), loc.get("country")]
                        loc_list.append(", ".join(p for p in parts if p))
                location = " | ".join(loc_list)

            dept = post.get("department") or {}
            department = dept.get("name") or "" if isinstance(dept, dict) else str(dept)

            payload_item = {
                "id": ats_id,
                "title": title,
                "location": location,
                "department": department,
                "employment_type": post.get("employmentType") or "",
                "url": f"https://jobs.gem.com/{slug}/{ats_id}",
            }

            yield RawJob(
                company_id=board.company_id,
                provider="gem",
                board_identity=board.identity,
                payload=payload_item,
            )

        logger.info(f"GemConnector[{slug}] - Extracted {len(seen)} jobs.")

    def _extract_slug(self, endpoint: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(endpoint)
        path = parsed.path.strip("/")
        return path.split("/")[0] if path else "unknown"

ConnectorRegistry.register("gem", "GraphQL", 10, GemConnector)
