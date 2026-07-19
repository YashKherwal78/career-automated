import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("WellfoundConnector")


class WellfoundConnector(Connector):
    """Wellfound (AngelList) connector — uses the public GraphQL API."""

    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="cursor",
            supports_etag=False,
            supports_last_modified=False,
            supports_content_hash=True,
            supports_incremental=False,
            supports_parallel_fetch=False,
            supports_snapshot=True,
            supports_departments=True,
            supports_location=True,
            supports_remote=True,
            supports_salary=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        # Wellfound's public job listing API
        api_url = "https://wellfound.com/graphql"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; CareerAutomated/1.0)",
        }

        slug = self._extract_slug(board.endpoint)
        query = """
        query CompanyJobs($slug: String!) {
            startup(slug: $slug) {
                name
                highlightedJobListings {
                    id
                    title
                    slug
                    description
                    remote
                    primaryRoleTitle
                    liveStartAt
                    compensation
                    locationNames
                    jobType
                }
            }
        }
        """

        payload = {"query": query, "variables": {"slug": slug}}
        result = await http_client.fetch("POST", api_url, headers=headers, json=payload)
        should_sync = self.freshness_strategy().should_sync(board, result)
        yield result

        if not should_sync:
            return

        if result.status_code != 200 or not isinstance(result.payload, dict):
            return

        data = result.payload.get("data", {}).get("startup", {}) or {}
        jobs = data.get("highlightedJobListings") or []

        seen = set()
        for job in jobs:
            if not isinstance(job, dict):
                continue
            ats_id = str(job.get("id") or "")
            if not ats_id or ats_id in seen:
                continue
            seen.add(ats_id)

            title = job.get("title") or ""
            if not title:
                continue

            locations = job.get("locationNames") or []
            location = ", ".join(locations) if isinstance(locations, list) else str(locations)
            remote = "Remote" if job.get("remote") else ""

            job_payload = {
                "id": ats_id,
                "title": title,
                "location": location,
                "remote": remote,
                "department": job.get("primaryRoleTitle") or "",
                "employment_type": job.get("jobType") or "",
                "description": job.get("description") or "",
                "url": f"https://wellfound.com/company/{slug}/jobs/{ats_id}",
                "created_at": job.get("liveStartAt") or "",
            }

            yield RawJob(
                company_id=board.company_id,
                provider="wellfound",
                board_identity=board.identity,
                payload=job_payload,
            )

        logger.info(f"WellfoundConnector[{slug}] - Extracted {len(seen)} jobs.")

    def _extract_slug(self, endpoint: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(endpoint)
        path = parsed.path.strip("/")
        parts = path.split("/")
        # Expects /company/{slug} or just /{slug}
        if "company" in parts:
            idx = parts.index("company")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        return parts[-1] if parts else "unknown"


ConnectorRegistry.register("wellfound", "GraphQL", 10, WellfoundConnector)
