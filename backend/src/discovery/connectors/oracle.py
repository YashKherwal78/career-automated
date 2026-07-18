import logging
import re
from urllib.parse import urlparse
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

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
        
    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        # Oracle HCM endpoints are stored as:
        #   https://<tenant>.fa.<region>.oraclecloud.com/hcmUI/CandidateExperience/en/sites/<site>
        # Build the REST API URL from the same host:
        parsed = urlparse(board.endpoint)
        api_url = (
            f"{parsed.scheme}://{parsed.netloc}"
            f"/hcmRestApi/resources/latest/recruitingCEJobRequisitionsWithRssDetails"
        )
        result = await http_client.fetch("GET", api_url, headers={"Accept": "application/json"})
        yield result
        if result.status_code == 200 and isinstance(result.payload, dict):
            for job in result.payload.get("items", []):
                yield RawJob(company_id=board.company_id, provider="oracle", board_identity=board.identity, payload=job)
        elif result.status_code in (401, 403):
            logger.info(f"OracleJSONConnector[{parsed.netloc}] - REST API requires auth (HTTP {result.status_code}). Skipping.")
        else:
            logger.debug(f"OracleJSONConnector[{parsed.netloc}] - HTTP {result.status_code}. No jobs extracted.")

ConnectorRegistry.register('oracle', 'JSON', 100, OracleJSONConnector)
