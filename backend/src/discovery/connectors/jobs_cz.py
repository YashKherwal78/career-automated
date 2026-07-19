import logging
import re
from typing import AsyncIterator
from bs4 import BeautifulSoup
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("JobsCzConnector")

_LOCATION_SEEDS = (
    "praha", "brno", "ostrava", "plzen", "liberec", "olomouc",
    "usti-nad-labem", "ceske-budejovice", "hradec-kralove", "pardubice",
    "zlin", "jihlava", "karlovy-vary", "zahranici"
)


class JobsCzConnector(Connector):
    """jobs.cz connector — Czech Republic's leading job search engine."""

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
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.5",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        # We will parse one of the major location seeds (defaulting to praha if endpoint is generic)
        seed = "praha"
        endpoint_url = board.endpoint.rstrip("/")
        for s in _LOCATION_SEEDS:
            if s in endpoint_url.lower():
                seed = s
                break

        page = 1
        max_pages = 10
        seen = set()

        while page <= max_pages:
            url = f"https://www.jobs.cz/prace/{seed}/"
            params = {"page": page} if page > 1 else None

            result = await http_client.fetch("GET", url, headers=headers, params=params)

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
            cards = soup.select("article.SearchResultCard")
            if not cards:
                break

            page_count = 0
            for card in cards:
                link = card.select_one("a[data-jobad-id]")
                if not link:
                    continue
                ats_id = (link.get("data-jobad-id") or "").strip()
                if not ats_id or ats_id in seen:
                    continue
                seen.add(ats_id)
                page_count += 1

                title = (link.get("data-test-ad-title") or link.get_text(strip=True) or "").strip()
                href = link.get("href") or ""
                job_url = href.split("?")[0]
                if job_url.startswith("/"):
                    job_url = f"https://www.jobs.cz{job_url}"

                company_el = card.select_one("span[translate='no']")
                company = company_el.get_text(strip=True) if company_el else ""

                loc_el = card.select_one("li[data-test='serp-locality']")
                location = loc_el.get_text(" ", strip=True) if loc_el else ""

                body = card.select_one("div.SearchResultCard__body")
                salary = ""
                if body:
                    success_tag = body.select_one("span.Tag.Tag--success")
                    if success_tag:
                        salary = success_tag.get_text(strip=True)

                payload_item = {
                    "id": ats_id,
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": job_url,
                    "salary": salary,
                }

                yield RawJob(
                    company_id=board.company_id,
                    provider="jobs_cz",
                    board_identity=board.identity,
                    payload=payload_item,
                )

            if page_count == 0 or len(cards) < 20:
                break
            page += 1

        logger.info(f"JobsCzConnector - Extracted {len(seen)} jobs across {page - 1} pages.")


ConnectorRegistry.register("jobs_cz", "HTML", 10, JobsCzConnector)
