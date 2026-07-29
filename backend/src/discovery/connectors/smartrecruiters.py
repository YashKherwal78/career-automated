from typing import AsyncIterator, Optional
import logging
from src.discovery.models import RawJob, ConnectorCapability, Board
from src.discovery.registry.connector import Connector
from src.discovery.registry.connector_registry import ConnectorRegistry
from src.discovery.detail_fetch import DetailFetchThrottle, get_cached_description, cache_description
from src.discovery.html_text import strip_html

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

    async def _fetch_description(
        self, slug: str, job_id: str, http_client, throttle: DetailFetchThrottle
    ) -> Optional[str]:
        """
        SmartRecruiters' list endpoint never includes the job ad body — it
        lives behind GET /v1/companies/{slug}/postings/{id}, in
        jobAd.sections.jobDescription.text.
        """
        if not job_id:
            return None

        cached = get_cached_description("smartrecruiters", job_id)
        if cached is not None:
            return cached

        await throttle.wait()
        detail_url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings/{job_id}"
        try:
            result = await http_client.fetch("GET", detail_url)
        except Exception as e:
            logger.debug("SmartRecruitersConnector: detail fetch failed for %s: %s", job_id, e)
            return None

        if result.status_code != 200 or not isinstance(result.payload, dict):
            return None

        sections = result.payload.get("jobAd", {}).get("sections", {}) if isinstance(result.payload.get("jobAd"), dict) else {}
        raw_desc = sections.get("jobDescription", {}).get("text", "") if isinstance(sections.get("jobDescription"), dict) else ""
        description = strip_html(raw_desc)
        cache_description("smartrecruiters", job_id, description)
        return description

    async def sync(self, board: Board, http_client) -> AsyncIterator[RawJob]:
        slug = board.endpoint.rstrip("/").split("/")[-1]
        api_url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
        throttle = DetailFetchThrottle(requests_per_second=5.0)

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
                job["description"] = await self._fetch_description(
                    slug, str(job.get("id", "")), http_client, throttle
                ) or ""
                yield RawJob(company_id=board.company_id, provider="smartrecruiters", board_identity=board.identity, payload=job)

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
                job["description"] = await self._fetch_description(
                    slug, str(job.get("id", "")), http_client, throttle
                ) or ""
                yield RawJob(company_id=board.company_id, provider="smartrecruiters", board_identity=board.identity, payload=job)

            if len(content) < limit:
                break

            offset += limit

ConnectorRegistry.register('smartrecruiters', 'HTML', 10, SmartRecruitersConnector)
