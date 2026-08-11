import json
import logging
import re
from urllib.parse import urlparse
from typing import AsyncIterator
from bs4 import BeautifulSoup
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry
from src.discovery.html_text import strip_html

logger = logging.getLogger("PhenomConnector")

_CSRF_RE = re.compile(r'csrfToken["\']?\s*:\s*["\']([^"\']+)["\']')


class PhenomConnector(Connector):
    """Phenom connector — POSTs search requests to /widgets with CSRF token."""

    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="offset",
            supports_etag=False,
            supports_last_modified=False,
            supports_content_hash=True,
            supports_incremental=False,
            supports_parallel_fetch=False,
            supports_snapshot=True,
            supports_location=True,
            supports_departments=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        parsed = urlparse(board.endpoint)
        base_url = f"{parsed.scheme}://{parsed.hostname}"

        # Parse country and locale from endpoint if possible, default to us / en_us
        country = "us"
        locale = "en_us"
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) >= 2:
            country = path_parts[0]
            locale = path_parts[1].replace("-", "_")

        # 1. Initialize session to get CSRF token
        search_results_url = f"{base_url}/{country}/{locale.split('_')[0]}/search-results"
        init_res = await http_client.fetch("GET", search_results_url, headers={"User-Agent": "Mozilla/5.0"})
        if init_res.status_code != 200:
            logger.warning(f"PhenomConnector - Session init failed {init_res.status_code}")
            yield init_res
            return

        html_text = init_res.payload
        if isinstance(html_text, bytes):
            html_text = html_text.decode("utf-8", errors="replace")
        if not isinstance(html_text, str):
            yield init_res
            return

        csrf = ""
        # Look in cookies
        cookies_header = init_res.response_headers.get("Set-Cookie") or ""
        cookie_match = re.search(r'csrf[^=]*=([^;]+)', cookies_header, re.IGNORECASE)
        if cookie_match:
            csrf = cookie_match.group(1)
        else:
            match = _CSRF_RE.search(html_text)
            csrf = match.group(1) if match else ""

        # 2. Query widgets endpoint
        url = f"{base_url}/widgets"
        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Origin": base_url,
            "Referer": search_results_url,
            "User-Agent": "Mozilla/5.0",
        }
        if csrf:
            headers["x-csrf-token"] = csrf

        start = 0
        page_size = 50
        seen = set()

        while True:
            payload = {
                "lang": locale,
                "deviceType": "desktop",
                "country": country,
                "pageName": "search-results",
                "ddoKey": "refineSearch",
                "from": start,
                "jobs": True,
                "counts": True,
                "size": page_size,
            }
            result = await http_client.fetch("POST", url, headers=headers, json=payload)
            
            if start == 0:
                should_sync = self.freshness_strategy().should_sync(board, result)
                yield result
                if not should_sync:
                    return

            if result.status_code != 200 or not isinstance(result.payload, dict):
                break

            rs = result.payload.get("refineSearch") or {}
            jobs = []
            if isinstance(rs, dict):
                data = rs.get("data") or {}
                jobs = data.get("jobs") or rs.get("jobs") or rs.get("hits") or []
            if not jobs and isinstance(result.payload.get("jobs"), list):
                jobs = result.payload["jobs"]

            if not jobs:
                break

            page_count = 0
            for item in jobs:
                if not isinstance(item, dict):
                    continue
                ats_id = str(item.get("jobId") or item.get("id") or "")
                if not ats_id or ats_id in seen:
                    continue
                seen.add(ats_id)
                page_count += 1

                title = item.get("title") or item.get("jobTitle") or ""
                if not title:
                    continue

                # Location formatting
                location = ""
                city = item.get("city") or ""
                state = item.get("state") or ""
                cntry = item.get("country") or ""
                location = ", ".join(p for p in [city, state, cntry] if p)

                job_url = item.get("applyUrl") or item.get("jobUrl") or item.get("url") or ""
                if job_url and not job_url.startswith("http"):
                    job_url = f"{base_url}{job_url if job_url.startswith('/') else '/' + job_url}"
                if not job_url:
                    # The refineSearch job entries carry no url/applyUrl/jobUrl field at
                    # all in real payloads (verified live against careers.phenom.com) —
                    # but the detail page URL only needs the jobId, any slug works.
                    job_url = f"{base_url}/{country}/{locale.split('_')[0]}/job/{ats_id}/job"

                description = await self._fetch_description(http_client, job_url, ats_id)

                payload_item = {
                    "id": ats_id,
                    "title": title,
                    "location": location,
                    "url": job_url,
                    "department": item.get("department") or item.get("category") or "",
                    "employment_type": item.get("jobType") or "",
                    "description": description,
                }

                yield RawJob(
                    company_id=board.company_id,
                    provider="phenom",
                    board_identity=board.identity,
                    payload=payload_item,
                )

            if page_count == 0 or len(jobs) < page_size:
                break
            start += len(jobs)

        logger.info(f"PhenomConnector - Extracted {len(seen)} jobs.")

    async def _fetch_description(self, http_client: HttpClient, job_url: str, ats_id: str) -> str:
        """Fetch the job detail page and extract the JobPosting JSON-LD description.

        The /widgets refineSearch response only has a short "descriptionTeaser"
        field (verified live against careers.phenom.com), not the full
        description, so this fetches the detail page and reads the
        `<script type="application/ld+json">` JobPosting block instead.
        """
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            detail_result = await http_client.fetch("GET", job_url, headers=headers)
        except Exception as exc:
            logger.warning(f"PhenomConnector - Detail fetch failed for job {ats_id}: {exc}")
            return ""

        if detail_result.status_code != 200:
            logger.warning(f"PhenomConnector - Detail HTTP {detail_result.status_code} for job {ats_id}")
            return ""

        detail_html = detail_result.payload
        if isinstance(detail_html, bytes):
            detail_html = detail_html.decode("utf-8", errors="replace")
        if not isinstance(detail_html, str):
            return ""

        try:
            soup = BeautifulSoup(detail_html, "html.parser")
            for script in soup.find_all("script", type="application/ld+json"):
                if not script.string:
                    continue
                try:
                    data = json.loads(script.string)
                except (ValueError, TypeError):
                    continue
                if isinstance(data, dict) and data.get("@type") == "JobPosting":
                    # description is HTML that's itself HTML-entity-escaped
                    # (verified: <strong> shows up as &lt;strong&gt;), so
                    # strip_html's own unescape+tag-strip needs to run twice.
                    return strip_html(strip_html(data.get("description") or ""))
            return ""
        except Exception as exc:
            logger.warning(f"PhenomConnector - Failed to parse description for job {ats_id}: {exc}")
            return ""


ConnectorRegistry.register("phenom", "JSON", 10, PhenomConnector)
