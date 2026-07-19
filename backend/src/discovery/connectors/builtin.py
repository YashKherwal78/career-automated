import logging
import re
import json
import html as html_lib
from typing import AsyncIterator
from src.discovery.models import RawJob, ConnectorCapability, Board, FetchResult
from src.discovery.registry.connector import Connector, FreshnessStrategy, DefaultFreshnessStrategy
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.registry.connector_registry import ConnectorRegistry

logger = logging.getLogger("BuiltInConnector")

_LD_RE = re.compile(
    r'<script[^>]+type="application/ld(?:\+|&#x2B;)json"[^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)
_JOB_URL_ID_RE = re.compile(r"^https?://[^/]+/job/[^/]+/(?P<id>\d+)/?$")


class BuiltInConnector(Connector):
    """Built In connector — parses JSON-LD from public listing pages."""

    def capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(
            pagination="page",
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
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        page = 1
        max_pages = 25
        seen = set()

        while page <= max_pages:
            url = f"https://builtin.com/jobs?page={page}"
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
            if not isinstance(html_text, str):
                break

            # Parse JSON-LD ItemList
            page_count = 0
            for match in _LD_RE.finditer(html_text):
                try:
                    payload = json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue

                graph = payload.get("@graph", [payload]) if isinstance(payload, dict) else payload
                if not isinstance(graph, list):
                    graph = [graph]

                for node in graph:
                    if not isinstance(node, dict):
                        continue
                    if node.get("@type") == "ItemList":
                        items = node.get("itemListElement") or []
                        for it in items:
                            if not isinstance(it, dict):
                                continue
                            job_url = (it.get("url") or "").strip()
                            title = (it.get("name") or "").strip()
                            if not job_url or not title:
                                continue

                            url_match = _JOB_URL_ID_RE.match(job_url)
                            ats_id = url_match.group("id") if url_match else ""
                            if not ats_id or ats_id in seen:
                                continue
                            seen.add(ats_id)
                            page_count += 1

                            desc = it.get("description") or ""
                            if desc:
                                desc = html_lib.unescape(desc)

                            payload_item = {
                                "id": ats_id,
                                "title": title,
                                "url": job_url,
                                "description": desc,
                            }

                            yield RawJob(
                                company_id=board.company_id,
                                provider="builtin",
                                board_identity=board.identity,
                                payload=payload_item,
                            )

            if page_count == 0:
                break
            page += 1

        logger.info(f"BuiltInConnector - Extracted {len(seen)} jobs across {page - 1} pages.")


ConnectorRegistry.register("builtin", "HTML", 10, BuiltInConnector)
