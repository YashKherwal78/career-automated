import logging
import xml.etree.ElementTree as ET
from typing import AsyncIterator, Dict
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry
from src.discovery.html_text import strip_html

logger = logging.getLogger("PersonioConnector")

# Personio exposes JSON at two possible endpoints per tenant
ENDPOINTS = ("/search.json", "/api/careers/jobs/list/")


class PersonioConnector(Connector):

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
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        base_url = self._resolve_base_url(board.endpoint)
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        result = None
        items = []

        for path in ENDPOINTS:
            url = f"{base_url}{path}"
            result = await http_client.fetch("GET", url, headers=headers)
            if result.status_code == 200 and isinstance(result.payload, (dict, list)):
                items = self._normalize_items(result.payload)
                if items:
                    break

        if result is None:
            return

        should_sync = self.freshness_strategy().should_sync(board, result)
        yield result

        if not should_sync:
            logger.info(f"PersonioConnector - Content unchanged. Skipping sync.")
            return

        if not items:
            logger.info(f"PersonioConnector - No jobs found.")
            return

        # The search.json/careers list endpoints always report an empty
        # "description" field — verified against a live board
        # (clark.jobs.personio.de). Full descriptions live in the board-wide
        # /xml feed, keyed by job id, so fetch it once per sync (not once per
        # job) and look descriptions up locally.
        descriptions = await self._fetch_descriptions(http_client, base_url)

        seen = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            ats_id = str(item.get("id") or item.get("jobId") or item.get("uuid") or "")
            if not ats_id or ats_id in seen:
                continue
            seen.add(ats_id)

            title = item.get("name") or item.get("title") or ""
            if not title:
                continue

            # Location
            location = ""
            office = item.get("office")
            if isinstance(office, str):
                location = office
            else:
                loc = item.get("location") or item.get("office") or {}
                if isinstance(loc, str):
                    location = loc
                elif isinstance(loc, dict):
                    location = loc.get("name") or loc.get("city") or ""

            # Department
            department = item.get("department")
            if isinstance(department, dict):
                department = department.get("name") or ""
            elif not isinstance(department, str):
                department = ""

            employment_type = item.get("employment_type") or item.get("employmentType") or item.get("schedule") or ""

            job_url = item.get("url") or f"{base_url}/job/{ats_id}"

            payload = {
                "id": ats_id,
                "title": title,
                "location": location,
                "department": department,
                "employment_type": employment_type,
                "url": job_url,
                "created_at": item.get("createdAt") or item.get("created_at") or "",
                "description": descriptions.get(ats_id, ""),
            }

            yield RawJob(
                company_id=board.company_id,
                provider="personio",
                board_identity=board.identity,
                payload=payload,
            )

        logger.info(f"PersonioConnector - Extracted {len(seen)} jobs.")

    async def _fetch_descriptions(self, http_client: HttpClient, base_url: str) -> Dict[str, str]:
        """Fetch the board-wide XML feed and build a job id -> plain-text description map.

        Unlike most of the other broken connectors, Personio's board data
        doesn't require a per-job request: /xml returns every job's full
        description (as <jobDescriptions><jobDescription><name>/<value> pairs)
        in a single response, so we fetch it once per sync.
        """
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/xml, application/xml"}
        try:
            result = await http_client.fetch("GET", f"{base_url}/xml", headers=headers)
        except Exception as exc:
            logger.warning(f"PersonioConnector - XML description fetch failed: {exc}")
            return {}

        if result.status_code != 200 or not result.payload:
            logger.warning(f"PersonioConnector - XML description fetch HTTP {result.status_code}")
            return {}

        raw = result.payload
        if isinstance(raw, (dict, list)):
            # aiohttp tried (and failed) to treat this as JSON already handled it as bytes;
            # if it somehow parsed as JSON this feed is not XML, bail out.
            return {}
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        if not isinstance(raw, str):
            return {}

        descriptions: Dict[str, str] = {}
        try:
            root = ET.fromstring(raw)
            for job_el in root.findall("position") or list(root):
                id_el = job_el.find("id")
                if id_el is None or not (id_el.text or "").strip():
                    continue
                job_id = id_el.text.strip()

                sections = []
                job_descs = job_el.find("jobDescriptions")
                if job_descs is not None:
                    for section in job_descs.findall("jobDescription"):
                        name_el = section.find("name")
                        value_el = section.find("value")
                        if name_el is not None and (name_el.text or "").strip():
                            sections.append(name_el.text.strip())
                        if value_el is not None and (value_el.text or "").strip():
                            sections.append(value_el.text.strip())

                if sections:
                    descriptions[job_id] = strip_html(" ".join(sections))
        except Exception as exc:
            logger.warning(f"PersonioConnector - Failed to parse XML descriptions: {exc}")
            return {}

        return descriptions

    def _resolve_base_url(self, endpoint: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(endpoint)
        hostname = parsed.hostname or ""
        if ".jobs.personio." in hostname or ".personio." in hostname:
            return f"{parsed.scheme or 'https'}://{hostname}"
        # Assume the endpoint is a full URL
        return endpoint.rstrip("/")

    def _normalize_items(self, payload) -> list:
        if isinstance(payload, list):
            return [p for p in payload if isinstance(p, dict)]
        if isinstance(payload, dict):
            for key in ("data", "jobs", "results", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [p for p in value if isinstance(p, dict)]
        return []


ConnectorRegistry.register("personio", "JSON", 10, PersonioConnector)
