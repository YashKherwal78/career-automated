import json
import logging
import re
from typing import AsyncIterator, Optional
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry
from src.discovery.detail_fetch import DetailFetchThrottle, get_cached_description, cache_description
from src.discovery.html_text import strip_html

_JSONLD_RE = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(?P<json>.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)

logger = logging.getLogger("BreezyHRConnector")


class BreezyHRConnector(Connector):
    """BreezyHR connector — uses the public JSON endpoint at /json."""

    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="none",
            supports_etag=False,
            supports_last_modified=False,
            supports_content_hash=True,
            supports_incremental=False,
            supports_parallel_fetch=False,
            supports_snapshot=True,
            supports_departments=True,
            supports_location=True,
            supports_remote=True,
            supports_salary=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def _fetch_description(
        self, job_url: str, http_client: HttpClient, throttle: DetailFetchThrottle
    ) -> Optional[str]:
        """
        The /json positions list never includes the JD body. The guessed
        /p/{id}.json detail endpoint doesn't actually return JSON (it falls
        back to the SPA's index HTML) — verified against a live posting. The
        real, reliable source is the schema.org JobPosting JSON-LD block
        already embedded in the job's own HTML page (there are multiple
        ld+json blocks on the page; only one has @type == "JobPosting").
        """
        if not job_url:
            return None

        cached = get_cached_description("breezy", job_url)
        if cached is not None:
            return cached

        await throttle.wait()
        try:
            result = await http_client.fetch(
                "GET", job_url, headers={"User-Agent": "Mozilla/5.0 (compatible; CareerAutomated/1.0)"}
            )
        except Exception as e:
            logger.debug("BreezyHRConnector: detail fetch failed for %s: %s", job_url, e)
            return None

        if result.status_code != 200:
            return None

        html_text = result.payload
        if isinstance(html_text, bytes):
            html_text = html_text.decode("utf-8", errors="replace")
        if not isinstance(html_text, str):
            return None

        description = ""
        for match in _JSONLD_RE.finditer(html_text):
            try:
                data = json.loads(match.group("json"))
            except Exception:
                continue
            if isinstance(data, dict) and data.get("@type") == "JobPosting":
                description = strip_html(data.get("description", ""))
                break

        cache_description("breezy", job_url, description)
        return description

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        slug = self._extract_slug(board.endpoint)
        api_url = f"https://{slug}.breezy.hr/json"
        headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0 (compatible; CareerAutomated/1.0)"}
        throttle = DetailFetchThrottle(requests_per_second=5.0)

        result = await http_client.fetch("GET", api_url, headers=headers)
        should_sync = self.freshness_strategy().should_sync(board, result)
        yield result

        if not should_sync:
            logger.info(f"BreezyHRConnector[{slug}] - Content unchanged.")
            return

        if result.status_code != 200:
            logger.warning(f"BreezyHRConnector[{slug}] - HTTP {result.status_code}")
            return

        positions = result.payload if isinstance(result.payload, list) else []
        seen = set()

        for pos in positions:
            if not isinstance(pos, dict):
                continue
            ats_id = str(pos.get("id") or "")
            if not ats_id or ats_id in seen:
                continue
            seen.add(ats_id)

            title = pos.get("name") or pos.get("title") or ""
            if not title:
                continue

            # Location
            loc = pos.get("location") or {}
            location = ""
            if isinstance(loc, dict):
                parts = []
                for k in ("city", "state", "country"):
                    val = loc.get(k)
                    if isinstance(val, dict):
                        parts.append(val.get("name") or val.get("name_en") or val.get("code") or "")
                    elif val:
                        parts.append(str(val))
                location = ", ".join(p for p in parts if p.strip())
            elif isinstance(loc, str):
                location = loc

            remote = "Remote" if (isinstance(loc, dict) and loc.get("is_remote")) else ""
            department = pos.get("department") or ""

            # Employment type
            emp_type = pos.get("type") or ""
            if isinstance(emp_type, dict):
                emp_type = emp_type.get("id") or emp_type.get("name") or ""
            _type_map = {
                "fullTime": "FULL_TIME", "partTime": "PART_TIME",
                "contract": "CONTRACT", "intern": "INTERN", "internship": "INTERN",
                "temporary": "TEMPORARY",
            }
            emp_type = _type_map.get(emp_type, emp_type)

            # Salary
            salary_min = None
            salary_max = None
            salary_obj = pos.get("salary") or {}
            if isinstance(salary_obj, dict):
                salary_min = salary_obj.get("min")
                salary_max = salary_obj.get("max")

            job_url = pos.get("url") or f"https://{slug}.breezy.hr/p/{ats_id}"
            description = await self._fetch_description(job_url, http_client, throttle) or ""

            payload = {
                "id": ats_id,
                "title": title,
                "location": location,
                "remote": remote,
                "department": department,
                "employment_type": emp_type,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "url": job_url,
                "created_at": pos.get("published_date") or pos.get("creation_date") or "",
                "description": description,
            }

            yield RawJob(
                company_id=board.company_id,
                provider="breezy",
                board_identity=board.identity,
                payload=payload,
            )

        logger.info(f"BreezyHRConnector[{slug}] - Extracted {len(seen)} jobs.")

    def _extract_slug(self, endpoint: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(endpoint)
        hostname = parsed.hostname or ""
        if hostname.endswith(".breezy.hr") and hostname != "breezy.hr":
            return hostname.replace(".breezy.hr", "")
        parts = [p for p in parsed.path.strip("/").split("/") if p and p != "careers"]
        if parts:
            return parts[0]
        return hostname.replace(".breezy.hr", "") or "unknown"



ConnectorRegistry.register("breezy", "JSON", 10, BreezyHRConnector)
