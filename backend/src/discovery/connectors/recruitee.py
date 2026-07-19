import logging
import re
import html as html_lib
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("RecruiteeConnector")

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(text: str) -> str:
    text = _TAG_RE.sub(" ", text)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


class RecruiteeConnector(Connector):
    """Recruitee connector — uses the public JSON API at /api/offers."""

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
        api_url = self._resolve_api_url(board.endpoint)
        headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0 (compatible; CareerAutomated/1.0)"}

        result = await http_client.fetch("GET", api_url, headers=headers)
        should_sync = self.freshness_strategy().should_sync(board, result)
        yield result

        if not should_sync:
            logger.info(f"RecruiteeConnector - Content unchanged. Skipping sync.")
            return

        if result.status_code != 200 or not isinstance(result.payload, dict):
            logger.warning(f"RecruiteeConnector - HTTP {result.status_code}")
            return

        offers = result.payload.get("offers") or []
        seen = set()

        for offer in offers:
            if not isinstance(offer, dict):
                continue

            ats_id = str(offer.get("id") or offer.get("slug") or "")
            if not ats_id or ats_id in seen:
                continue
            seen.add(ats_id)

            title = offer.get("title") or offer.get("position") or ""
            if not title:
                continue

            # Location
            location = ""
            if isinstance(offer.get("location"), str) and offer["location"].strip():
                location = offer["location"].strip()
            else:
                parts = [offer.get("city"), offer.get("state_code"), offer.get("country_code")]
                location = ", ".join(p for p in parts if p) or ""

            # Remote
            remote = ""
            if isinstance(offer.get("remote"), bool) and offer["remote"]:
                remote = "Remote"

            # Department
            department = offer.get("department") or offer.get("department_name") or ""

            # Employment type
            emp_type = offer.get("employment_type_code") or offer.get("employment_type") or ""

            # Salary
            salary_obj = offer.get("salary") if isinstance(offer.get("salary"), dict) else {}
            salary_min = self._to_float(salary_obj.get("min")) if salary_obj else None
            salary_max = self._to_float(salary_obj.get("max")) if salary_obj else None
            salary_currency = salary_obj.get("currency", "") if salary_obj else ""

            # Description
            description = ""
            for key in ("description", "requirements"):
                value = offer.get(key)
                if isinstance(value, str) and value.strip():
                    cleaned = _strip_tags(value)
                    if cleaned:
                        description += cleaned + "\n\n"
            description = description.strip()[:25000]

            # URL
            job_url = offer.get("careers_url") or offer.get("careers_apply_url") or ""

            payload = {
                "id": ats_id,
                "title": title,
                "location": location,
                "remote": remote,
                "department": department,
                "employment_type": emp_type,
                "description": description,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_currency": salary_currency,
                "url": job_url,
                "created_at": offer.get("created_at") or offer.get("published_at") or "",
            }

            yield RawJob(
                company_id=board.company_id,
                provider="recruitee",
                board_identity=board.identity,
                payload=payload,
            )

        logger.info(f"RecruiteeConnector - Extracted {len(seen)} jobs.")

    def _resolve_api_url(self, endpoint: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(endpoint)
        hostname = parsed.hostname or ""
        if ".recruitee.com" in hostname:
            slug = hostname.split(".recruitee.com")[0]
            return f"https://{slug}.recruitee.com/api/offers"
        # Custom domain or full URL
        base = endpoint.rstrip("/")
        if not base.endswith("/api/offers"):
            base = f"{base}/api/offers"
        return base

    def _to_float(self, value) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


ConnectorRegistry.register("recruitee", "JSON", 10, RecruiteeConnector)
