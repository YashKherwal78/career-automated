import logging
import re
import html as html_lib
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("WeWorkRemotelyConnector")

_TAG_RE = re.compile(r"<[^>]+>")
_JOB_RE = re.compile(
    r'<li[^>]*>\s*<a[^>]+href="(/remote-jobs/[^"]+)"[^>]*>(.*?)</a>\s*</li>',
    re.DOTALL | re.IGNORECASE,
)


class WeWorkRemotelyConnector(Connector):
    """WeWorkRemotely connector — scrapes the public RSS feed."""

    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="none",
            supports_etag=False,
            supports_last_modified=False,
            supports_content_hash=True,
            supports_incremental=False,
            supports_parallel_fetch=False,
            supports_snapshot=True,
            supports_remote=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        # WeWorkRemotely has a public RSS feed per category
        rss_url = "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss"
        headers = {"Accept": "application/rss+xml, application/xml, text/xml", "User-Agent": "Mozilla/5.0 (compatible; CareerAutomated/1.0)"}

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

        # Parse RSS items
        items = re.findall(r"<item>(.*?)</item>", xml_text, re.DOTALL)
        seen = set()

        for item_xml in items:
            title_match = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", item_xml, re.DOTALL)
            link_match = re.search(r"<link>(.*?)</link>", item_xml)
            guid_match = re.search(r"<guid[^>]*>(.*?)</guid>", item_xml)
            pubdate_match = re.search(r"<pubDate>(.*?)</pubDate>", item_xml)
            desc_match = re.search(r"<description><!\[CDATA\[(.*?)\]\]></description>|<description>(.*?)</description>", item_xml, re.DOTALL)

            title = ""
            if title_match:
                title = title_match.group(1) or title_match.group(2) or ""
            title = html_lib.unescape(title.strip())

            link = link_match.group(1).strip() if link_match else ""
            guid = guid_match.group(1).strip() if guid_match else link

            if not title or not guid or guid in seen:
                continue
            seen.add(guid)

            # Extract company name from title format "Company: Job Title"
            company = ""
            if ":" in title:
                company, title = title.split(":", 1)
                company = company.strip()
                title = title.strip()

            pub_date = pubdate_match.group(1).strip() if pubdate_match else ""

            payload = {
                "id": guid,
                "title": title,
                "company": company,
                "location": "Remote",
                "remote": "Remote",
                "url": link if link.startswith("http") else f"https://weworkremotely.com{link}",
                "created_at": pub_date,
            }

            yield RawJob(
                company_id=board.company_id,
                provider="weworkremotely",
                board_identity=board.identity,
                payload=payload,
            )

        logger.info(f"WeWorkRemotelyConnector - Extracted {len(seen)} jobs.")


ConnectorRegistry.register("weworkremotely", "RSS", 10, WeWorkRemotelyConnector)
