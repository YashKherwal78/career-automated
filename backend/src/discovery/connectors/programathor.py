import logging
import re
import html
from typing import AsyncIterator
from bs4 import BeautifulSoup
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("ProgramathorConnector")


class ProgramathorConnector(Connector):
    """Programathor connector — parses Programathor Brazilian tech jobs board."""

    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="page",
            supports_etag=False,
            supports_last_modified=False,
            supports_content_hash=True,
            supports_incremental=False,
            supports_parallel_fetch=False,
            supports_snapshot=True,
            supports_location=True,
            supports_salary=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        }

        page = 1
        max_pages = 5
        seen = set()

        while page <= max_pages:
            url = f"https://programathor.com.br/jobs?page={page}"
            result = await http_client.fetch("GET", url, headers=headers)

            if page == 1:
                should_sync = self.freshness_strategy().should_sync(board, result)
                yield result
                if not should_sync:
                    return

            if result.status_code != 200:
                break

            html_text = result.payload
            if isinstance(html_text, bytes):
                html_text = html_text.decode("utf-8", errors="replace")
            if not isinstance(html_text, str) or not html_text:
                break

            soup = BeautifulSoup(html_text, "html.parser")
            cards = soup.select("div.cell-list")
            if not cards:
                break

            page_count = 0
            for card in cards:
                link = card.select_one("a[href*='/jobs/']")
                if not link:
                    continue
                href = link.get("href") or ""
                match = re.search(r"/jobs/(\d+)-", href)
                ats_id = match.group(1) if match else None
                if not ats_id or ats_id in seen:
                    continue
                seen.add(ats_id)
                page_count += 1

                title_el = card.select_one("h3")
                title = title_el.get_text(strip=True) if title_el else ""
                title = re.sub(r"\s*NOVA\s*$", "", title).strip()

                company = "Unknown"
                comp_el = card.select_one("i.fa-briefcase")
                if comp_el and comp_el.next_sibling:
                    company = comp_el.next_sibling.strip()

                location_raw = ""
                loc_el = card.select_one("i.fa-map-marker-alt")
                if loc_el and loc_el.next_sibling:
                    location_raw = loc_el.next_sibling.strip()
                location = f"{location_raw}, Brazil" if location_raw else "Brazil"

                salary = ""
                sal_el = card.select_one("i.fa-money-bill-alt")
                if sal_el and sal_el.next_sibling:
                    salary = sal_el.next_sibling.strip()

                payload_item = {
                    "id": ats_id,
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": f"https://programathor.com.br{href}",
                    "salary": salary,
                }

                yield RawJob(
                    company_id=board.company_id,
                    provider="programathor",
                    board_identity=board.identity,
                    payload=payload_item,
                )

            if page_count == 0 or len(cards) < 15:
                break
            page += 1

        logger.info(f"ProgramathorConnector - Extracted {len(seen)} jobs across {page - 1} pages.")


ConnectorRegistry.register("programathor", "HTML", 10, ProgramathorConnector)
