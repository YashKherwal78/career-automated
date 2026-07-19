import logging
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("PinpointConnector")


class PinpointConnector(Connector):
    """Pinpoint connector — uses the public JSON endpoint at /postings.json."""

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
            supports_salary=True,
            supports_remote=True,
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        slug = self._extract_slug(board.endpoint)
        api_url = f"https://{slug}.pinpointhq.com/postings.json"
        headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0 (compatible; CareerAutomated/1.0)"}

        result = await http_client.fetch("GET", api_url, headers=headers)
        should_sync = self.freshness_strategy().should_sync(board, result)
        yield result

        if not should_sync:
            logger.info(f"PinpointConnector[{slug}] - Content unchanged.")
            return

        if result.status_code != 200 or not isinstance(result.payload, dict):
            logger.warning(f"PinpointConnector[{slug}] - HTTP {result.status_code}")
            return

        postings = result.payload.get("data") or []
        seen = set()

        for posting in postings:
            if not isinstance(posting, dict):
                continue
            ats_id = str(posting.get("id") or "")
            if not ats_id or ats_id in seen:
                continue
            seen.add(ats_id)

            title = posting.get("title") or ""
            if not title:
                continue

            # Location
            loc = posting.get("location") or {}
            location = ""
            if isinstance(loc, dict):
                location = loc.get("name") or loc.get("city") or ""
            elif isinstance(loc, str):
                location = loc

            # Remote / workplace type
            workplace = posting.get("workplace_type") or ""
            remote = ""
            if workplace in ("remote", "hybrid"):
                remote = "Remote" if workplace == "remote" else "Hybrid"

            # Department
            job_obj = posting.get("job") or {}
            dept_obj = job_obj.get("department") or {} if isinstance(job_obj, dict) else {}
            department = dept_obj.get("name") or "" if isinstance(dept_obj, dict) else ""

            # Employment type
            emp_type = posting.get("employment_type") or ""

            # Salary
            salary_min = posting.get("compensation_minimum")
            salary_max = posting.get("compensation_maximum")
            salary_currency = posting.get("compensation_currency") or ""

            job_url = posting.get("url") or f"https://{slug}.pinpointhq.com/postings/{ats_id}"

            payload = {
                "id": ats_id,
                "title": title,
                "location": location,
                "remote": remote,
                "department": department,
                "employment_type": emp_type,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_currency": salary_currency,
                "url": job_url,
                "created_at": posting.get("published_at") or "",
            }

            yield RawJob(
                company_id=board.company_id,
                provider="pinpoint",
                board_identity=board.identity,
                payload=payload,
            )

        logger.info(f"PinpointConnector[{slug}] - Extracted {len(seen)} jobs.")

    def _extract_slug(self, endpoint: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(endpoint)
        hostname = parsed.hostname or ""
        if ".pinpointhq.com" in hostname:
            return hostname.split(".pinpointhq.com")[0]
        return hostname or "unknown"


ConnectorRegistry.register("pinpoint", "JSON", 10, PinpointConnector)
