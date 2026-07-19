import logging
import json
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("EuresConnector")


class EuresConnector(Connector):
    """EURES connector — aggregates vacancies across EU/EEA countries."""

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
        )

    def freshness_strategy(self) -> FreshnessStrategy:
        return DefaultFreshnessStrategy()

    async def sync(self, board: Board, http_client: HttpClient) -> AsyncIterator[RawJob | FetchResult]:
        api_url = "https://europa.eu/eures/api/jv-searchengine/public/jv-search/search"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        }

        page = 1
        page_size = 50
        max_pages = 40  # Crawl 2000 freshest positions per cycle
        seen = set()

        while page <= max_pages:
            body = {
                "resultsPerPage": page_size,
                "page": page,
                "sortSearch": "MOST_RECENT",
                "keywords": [],
                "publicationPeriod": None,
                "occupationUris": [],
                "skillUris": [],
                "requiredExperienceCodes": [],
                "positionScheduleCodes": [],
                "sectorCodes": [],
                "educationAndQualificationLevelCodes": [],
                "positionOfferingCodes": [],
                "locationCodes": ["de", "at", "be"],
                "euresFlagCodes": [],
                "otherBenefitsCodes": [],
                "requiredLanguages": [],
                "minNumberPost": None,
                "sessionId": "jobhive",
                "requestLanguage": "en",
            }
            result = await http_client.fetch("POST", api_url, headers=headers, json=body)

            if page == 1:
                should_sync = self.freshness_strategy().should_sync(board, result)
                yield result
                if not should_sync:
                    return

            if result.status_code != 200:
                break

            payload = result.payload
            if isinstance(payload, bytes):
                try:
                    payload = json.loads(payload.decode("utf-8", errors="replace"))
                except Exception:
                    break
            elif isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    break

            if not isinstance(payload, dict):
                break

            jvs = payload.get("jvs") or []
            if not jvs:
                break

            page_count = 0
            for item in jvs:
                if not isinstance(item, dict):
                    continue
                ats_id = str(item.get("uniqueIdentifier") or "")
                if not ats_id or ats_id in seen:
                    continue
                seen.add(ats_id)
                page_count += 1

                title = item.get("jobVacancyTitle") or ""
                if not title:
                    continue

                # Company name
                company = item.get("employerName") or ""

                # Location
                location = ""
                loc_list = item.get("locations") or []
                if loc_list and isinstance(loc_list, list):
                    first_loc = loc_list[0]
                    if isinstance(first_loc, dict):
                        location = first_loc.get("cityName") or first_loc.get("countryName") or ""

                payload_item = {
                    "id": ats_id,
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": f"https://europa.eu/eures/portal/jv-se/jv-details/{ats_id}?lang=en",
                    "description": item.get("description") or "",
                }

                yield RawJob(
                    company_id=board.company_id,
                    provider="eures",
                    board_identity=board.identity,
                    payload=payload_item,
                )

            if page_count == 0 or len(jvs) < page_size:
                break
            page += 1

        logger.info(f"EuresConnector - Extracted {len(seen)} jobs.")


ConnectorRegistry.register("eures", "JSON", 10, EuresConnector)
