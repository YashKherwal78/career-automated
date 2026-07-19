import json
import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from bs4 import BeautifulSoup
from src.discovery.models import ConnectorCapability

logger = logging.getLogger("shared_connector_framework")

@dataclass
class ProviderFingerprint:
    version: str
    parser_type: str
    schema_hash: str
    build_id: Optional[str] = None
    app_version: Optional[str] = None

@dataclass
class ProviderProfile:
    provider: str
    interface: str            # rest, graphql, nextjs, html, jsonld
    endpoint: str
    fingerprint: ProviderFingerprint
    capabilities: ConnectorCapability

class NextJsParser:
    """Helper utility to discover and extract Next.js SSR state blocks."""
    @staticmethod
    def extract_next_data(html_content: bytes) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            soup = BeautifulSoup(html_content.decode("utf-8", errors="replace"), "html.parser")
            script = soup.find("script", id="__NEXT_DATA__")
            if script and script.string:
                data = json.loads(script.string)
                build_id = data.get("buildId")
                return data, build_id
        except Exception as e:
            logger.error(f"Error parsing __NEXT_DATA__: {e}")
        return None, None
