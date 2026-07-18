import json
import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("TeamtailorJSONConnector")

class TeamtailorJSONConnector(Connector):
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
        # Teamtailor uses the JSONFeed standard at /jobs.json
        # The /api/v1/jobs endpoint requires an API key and returns 404 publicly.
        base = board.endpoint.rstrip("/")
        api_url = f"{base}/jobs.json"
        result = await http_client.fetch("GET", api_url)
        
        # Teamtailor may serve jobs.json with a non-JSON Content-Type,
        # causing HttpClient to return raw bytes instead of a parsed dict.
        # Decode bytes to dict manually so the snapshot path doesn't fail.
        if isinstance(result.payload, (bytes, bytearray)):
            try:
                result.payload = json.loads(result.payload.decode("utf-8"))
            except Exception:
                # If we can't decode, yield the raw result and bail
                yield result
                return
        
        yield result
        if result.status_code == 200 and isinstance(result.payload, dict):
            for item in result.payload.get("items", []):
                # Prefer the structured _jobposting sub-dict if present
                job_data = item.get("_jobposting") or item
                yield RawJob(company_id=board.company_id, provider="teamtailor", board_identity=board.identity, payload=job_data)

ConnectorRegistry.register('teamtailor', 'JSON', 100, TeamtailorJSONConnector)
