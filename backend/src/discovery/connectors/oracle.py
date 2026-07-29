import logging
from urllib.parse import urlparse
from typing import AsyncIterator, Optional
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry
from src.discovery.html_text import strip_html

logger = logging.getLogger("OracleJSONConnector")

class OracleJSONConnector(Connector):
    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="offset",
            supports_etag=False,
            supports_last_modified=False,
            supports_content_hash=True,
            supports_incremental=False,
            supports_parallel_fetch=False,
            supports_snapshot=True,
            supports_bulk_fetch=True,
            supports_location=True,
            supports_departments=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    def _extract_site_number(self, endpoint: str) -> Optional[str]:
        parts = urlparse(endpoint).path.strip("/").split("/")
        if "sites" in parts:
            idx = parts.index("sites")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        return None

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        """
        Oracle HCM's REST resource is recruitingCEJobRequisitions (NOT
        "...WithRssDetails", which doesn't exist — verified 404 live), and it
        requires a finder=findReqs;siteNumber={site} param plus
        expand=requisitionList&onlyData=true to get the actual job array back
        (verified against a live tenant: the bare resource call only returns
        search metadata/facets, never job data, which is why this previously
        looked like an auth wall — it wasn't one).
        """
        parsed = urlparse(board.endpoint)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        site_number = self._extract_site_number(board.endpoint) or "CX"

        limit = 25
        offset = 0
        seen = set()

        while True:
            api_url = (
                f"{base_url}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
                f"?finder=findReqs;siteNumber={site_number},limit={limit},offset={offset}"
                f"&expand=requisitionList&onlyData=true"
            )
            result = await http_client.fetch("GET", api_url, headers={"Accept": "application/json"})

            if offset == 0:
                should_sync = self.freshness_strategy().should_sync(board, result)
                yield result
                if not should_sync:
                    return

            if result.status_code != 200 or not isinstance(result.payload, dict):
                if result.status_code in (401, 403):
                    logger.info(f"OracleJSONConnector[{parsed.netloc}] - REST API requires auth (HTTP {result.status_code}). Skipping.")
                else:
                    logger.debug(f"OracleJSONConnector[{parsed.netloc}] - HTTP {result.status_code}. No jobs extracted.")
                return

            items = result.payload.get("items") or []
            search_item = items[0] if items else {}
            requisitions = search_item.get("requisitionList") or []
            total = search_item.get("TotalJobsCount") or 0

            if not requisitions:
                break

            page_count = 0
            for req in requisitions:
                if not isinstance(req, dict):
                    continue
                req_id = str(req.get("Id") or "")
                if not req_id or req_id in seen:
                    continue
                seen.add(req_id)
                page_count += 1

                payload = {
                    "id": req_id,
                    "title": req.get("Title") or "",
                    "location": req.get("PrimaryLocation") or "",
                    "department": req.get("Organization") or req.get("JobFamily") or "",
                    "employment_type": req.get("WorkplaceType") or "",
                    "description": strip_html(req.get("ShortDescriptionStr") or ""),
                    "posted_date": req.get("PostedDate") or "",
                    "url": f"{base_url}/hcmUI/CandidateExperience/en/sites/{site_number}/job/{req_id}",
                }

                yield RawJob(
                    company_id=board.company_id,
                    provider="oracle",
                    board_identity=board.identity,
                    payload=payload,
                )

            offset += len(requisitions)
            if page_count == 0 or offset >= total or len(requisitions) < limit:
                break

        logger.info(f"OracleJSONConnector[{parsed.netloc}] - Extracted {len(seen)} jobs.")

ConnectorRegistry.register('oracle', 'JSON', 100, OracleJSONConnector)
