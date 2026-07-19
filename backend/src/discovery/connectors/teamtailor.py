import logging
import xml.etree.ElementTree as ET
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("TeamtailorConnector")

class TeamtailorConnector(Connector):
    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="none",
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
        
    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        base = board.endpoint.rstrip("/")
        # Target the universal public RSS feed instead of the brittle jobs.json
        api_url = f"{base}/jobs.rss"
        
        result = await http_client.fetch("GET", api_url)
        yield result
        
        if result.status_code != 200 or not result.payload:
            return
            
        xml_data = result.payload
        if isinstance(xml_data, bytes):
            xml_data = xml_data.decode("utf-8", errors="replace")
            
        try:
            root = ET.fromstring(xml_data)
        except Exception as e:
            logger.error(f"Failed to parse Teamtailor RSS XML for {board.company_id}: {e}")
            return
            
        namespaces = {"tt": "https://teamtailor.com/locations"}
        
        # Iterate channel items
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            guid = (item.findtext("guid") or "").strip()
            desc = (item.findtext("description") or "").strip()
            
            # Extract location details
            location_str = None
            loc_el = item.find("tt:locations/tt:location", namespaces)
            if loc_el is not None:
                city = (loc_el.findtext("tt:city", namespaces=namespaces) or "").strip()
                country = (loc_el.findtext("tt:country", namespaces=namespaces) or "").strip()
                if city and country:
                    location_str = f"{city}, {country}"
                elif city or country:
                    location_str = city or country
                else:
                    location_str = (loc_el.findtext("tt:name", namespaces=namespaces) or "").strip()
            
            # Map elements into dictionary expected by TeamtailorNormalizer
            payload = {
                "id": guid,
                "title": title,
                "description": desc,
                "location": location_str,
                "url": link
            }
            
            yield RawJob(
                company_id=board.company_id,
                provider="teamtailor",
                board_identity=board.identity,
                payload=payload
            )

ConnectorRegistry.register('teamtailor', 'RSS', 100, TeamtailorConnector)
