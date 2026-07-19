import logging
import re
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("SuccessFactorsConnector")

class SuccessFactorsConnector(Connector):
    """SuccessFactors recruiting marketing connector — parses sitemal.xml RSS feed."""

    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="none",
            supports_etag=False,
            supports_last_modified=False,
            supports_content_hash=True,
            supports_incremental=False,
            supports_parallel_fetch=False,
            supports_snapshot=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        from urllib.parse import urlparse
        parsed = urlparse(board.endpoint)
        hostname = parsed.hostname or board.endpoint
        
        rss_url = f"https://{hostname}/sitemal.xml"
        headers = {"Accept": "application/rss+xml, application/xml, text/xml", "User-Agent": "Mozilla/5.0"}

        result = await http_client.fetch("GET", rss_url, headers=headers)
        should_sync = self.freshness_strategy().should_sync(board, result)
        yield result

        if not should_sync or result.status_code != 200:
            return

        xml_text = result.payload
        if isinstance(xml_text, bytes):
            xml_text = xml_text.decode("utf-8", errors="replace")
        if not isinstance(xml_text, str):
            return

        items = re.findall(r"<item>(.*?)</item>", xml_text, re.DOTALL)
        seen = set()

        for item_xml in items:
            title_match = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", item_xml, re.DOTALL)
            link_match = re.search(r"<link>(.*?)</link>", item_xml)
            guid_match = re.search(r"<guid[^>]*>(.*?)</guid>", item_xml)
            pubdate_match = re.search(r"<pubDate>(.*?)</pubDate>", item_xml)

            title = ""
            if title_match:
                title = title_match.group(1) or title_match.group(2) or ""
            import html as html_lib
            title = html_lib.unescape(title.strip())

            link = link_match.group(1).strip() if link_match else ""
            guid = guid_match.group(1).strip() if guid_match else link

            if not title or not guid or guid in seen:
                continue
            seen.add(guid)

            payload = {
                "id": guid,
                "title": title,
                "url": link,
                "created_at": pubdate_match.group(1).strip() if pubdate_match else "",
            }

            yield RawJob(
                company_id=board.company_id,
                provider="successfactors",
                board_identity=board.identity,
                payload=payload,
            )

        logger.info(f"SuccessFactorsConnector[{hostname}] - Extracted {len(seen)} jobs.")

ConnectorRegistry.register("successfactors", "RSS", 10, SuccessFactorsConnector)
