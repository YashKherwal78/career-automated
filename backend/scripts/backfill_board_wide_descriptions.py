"""
Backfill for providers whose description already ships in the board's own
LIST response -- no per-job detail fetch needed at all, just one refetch of
the list per company (verified live for all three: Pinpoint's
postings.json, Recruiterbox's openings endpoint, and SuccessFactors'
sitemal.xml RSS feed all embed the full JD inline). These normalizers
already read description correctly (commits 5affe1c / 75222fc) -- same
stale-pre-fix-rows problem as backfill_jd_descriptions.py, just a
different fetch shape: one board-wide request maps many job_ids to
descriptions, instead of one request per job.

Groups stale rows by company_id, does ONE list fetch per company, matches
returned items by id to the stale job_ids for that company, and writes
back whichever ones matched. Also clears embedding/jd_profile/jd_hash on
a successful write so EmbeddingBackfillWorker re-embeds from real content.

Usage:
    python3 scripts/backfill_board_wide_descriptions.py --provider pinpoint --limit 500
    python3 scripts/backfill_board_wide_descriptions.py --provider recruiterbox --limit 500
    python3 scripts/backfill_board_wide_descriptions.py --provider successfactors --limit 500
    python3 scripts/backfill_board_wide_descriptions.py --provider pinpoint --limit 50 --dry-run
"""
import argparse
import asyncio
import os
import re
import sys
from collections import defaultdict
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.db import get_connection, is_postgres  # noqa: E402
from src.discovery.pipeline.http_client import HttpClient  # noqa: E402
from src.discovery.html_text import strip_html  # noqa: E402

CONCURRENCY = 5


def _pinpoint_slug(apply_url: str) -> str | None:
    host = urlsplit(apply_url).netloc
    if ".pinpointhq.com" not in host:
        return None
    return host.split(".pinpointhq.com")[0]


async def _pinpoint_fetch(http_client, slug: str) -> dict:
    """Returns {job_id: description}."""
    url = f"https://{slug}.pinpointhq.com/postings.json"
    r = await http_client.fetch("GET", url, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
    if r.status_code != 200 or not isinstance(r.payload, dict):
        return {}
    out = {}
    for posting in r.payload.get("data") or []:
        if not isinstance(posting, dict):
            continue
        job_id = str(posting.get("id") or "")
        if job_id:
            out[job_id] = strip_html(posting.get("description") or "")
    return out


def _recruiterbox_slug(apply_url: str) -> str | None:
    host = urlsplit(apply_url).netloc
    if not host:
        return None
    return host.split(".")[0]


async def _recruiterbox_fetch(http_client, slug: str) -> dict:
    url = f"https://jsapi.recruiterbox.com/v1/openings?client_name={slug}"
    r = await http_client.fetch("GET", url, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
    if r.status_code != 200:
        return {}
    payload = r.payload
    objects = []
    if isinstance(payload, dict):
        objects = payload.get("objects") or payload.get("results") or payload.get("data") or []
    elif isinstance(payload, list):
        objects = payload
    out = {}
    for obj in objects:
        if not isinstance(obj, dict):
            continue
        job_id = str(obj.get("id") or "")
        if job_id:
            out[job_id] = strip_html(obj.get("description") or "")
    return out


def _successfactors_hostname(apply_url: str) -> str | None:
    host = urlsplit(apply_url).netloc
    return host or None


async def _successfactors_fetch(http_client, hostname: str) -> dict:
    """Returns {guid: description}, keyed the same way the connector keys
    normalized_jobs.job_id-adjacent 'id' -- guid falls back to link when a
    feed item has no <guid>, matching SuccessFactorsConnector.sync()."""
    url = f"https://{hostname}/sitemal.xml"
    r = await http_client.fetch(
        "GET", url, headers={"Accept": "application/rss+xml, application/xml, text/xml", "User-Agent": "Mozilla/5.0"}
    )
    if r.status_code != 200:
        return {}
    xml_text = r.payload
    if isinstance(xml_text, bytes):
        xml_text = xml_text.decode("utf-8", errors="replace")
    if not isinstance(xml_text, str):
        return {}

    out = {}
    for item_xml in re.findall(r"<item>(.*?)</item>", xml_text, re.DOTALL):
        link_match = re.search(r"<link>(.*?)</link>", item_xml)
        guid_match = re.search(r"<guid[^>]*>(.*?)</guid>", item_xml)
        desc_match = re.search(
            r"<description><!\[CDATA\[(.*?)\]\]></description>|<description>(.*?)</description>",
            item_xml, re.DOTALL,
        )
        link = link_match.group(1).strip() if link_match else ""
        guid = guid_match.group(1).strip() if guid_match else link
        if not guid:
            continue
        description = strip_html(desc_match.group(1) or desc_match.group(2) or "") if desc_match else ""
        out[guid] = description
    return out


PROVIDER_CONFIG = {
    "pinpoint": (_pinpoint_slug, _pinpoint_fetch),
    "recruiterbox": (_recruiterbox_slug, _recruiterbox_fetch),
    "successfactors": (_successfactors_hostname, _successfactors_fetch),
}


def _fetch_rows(provider: str, limit: int, offset: int = 0):
    """offset matters here too: a company whose board fetch fails (dead
    slug, board taken down) leaves ALL its rows in the WHERE-empty set, so
    a full-backlog sweep must advance offset each batch or it'll re-hit
    the same broken companies forever."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        ph = "%s" if is_postgres() else "?"
        cur.execute(
            f"""
            SELECT job_id, apply_url, raw_payload_json FROM normalized_jobs
            WHERE provider = {ph} AND status = 'ACTIVE'
              AND (description IS NULL OR description = '')
              AND apply_url IS NOT NULL AND apply_url != ''
            ORDER BY normalized_at DESC
            LIMIT {ph} OFFSET {ph}
            """,
            (provider, limit, offset),
        )
        rows = cur.fetchall()
        return [
            dict(row) if hasattr(row, "keys") else dict(zip([c[0] for c in cur.description], row))
            for row in rows
        ]
    finally:
        conn.close()


def _write_result(job_id: str, description: str):
    conn = get_connection()
    try:
        cur = conn.cursor()
        ph = "%s" if is_postgres() else "?"
        cur.execute(
            f"""
            UPDATE normalized_jobs
            SET description = {ph}, embedding = NULL, jd_profile = NULL, jd_hash = NULL, jd_parsed_at = NULL
            WHERE job_id = {ph}
            """,
            (description, job_id),
        )
        conn.commit()
    finally:
        conn.close()


async def run(provider: str, limit: int, dry_run: bool, offset: int = 0):
    slug_fn, fetch_fn = PROVIDER_CONFIG[provider]

    rows = _fetch_rows(provider, limit, offset)
    print(f"[{provider}] {len(rows)} candidate rows (empty description, ACTIVE, has apply_url)")
    if not rows:
        return

    by_key = defaultdict(list)
    unresolvable = 0
    for row in rows:
        import json as _json
        try:
            raw_payload = _json.loads(row.get("raw_payload_json") or "{}")
        except Exception:
            raw_payload = {}
        key = slug_fn(row["apply_url"])
        if not key:
            unresolvable += 1
            continue
        by_key[key].append((row["job_id"], str(raw_payload.get("id") or "")))

    print(f"[{provider}] {len(by_key)} distinct companies to fetch ({unresolvable} rows had no derivable key)")

    sem = asyncio.Semaphore(CONCURRENCY)
    stats = {"matched": 0, "no_match": 0, "board_fetch_failed": 0}

    async with HttpClient() as http_client:
        async def handle(key: str, job_pairs: list):
            async with sem:
                try:
                    id_to_desc = await fetch_fn(http_client, key)
                except Exception as e:
                    stats["board_fetch_failed"] += 1
                    print(f"  ERROR fetching board {key}: {e}")
                    return
                if not id_to_desc:
                    stats["board_fetch_failed"] += 1
                    return
                for job_id, ats_id in job_pairs:
                    description = id_to_desc.get(ats_id, "")
                    if description.strip():
                        stats["matched"] += 1
                        if not dry_run:
                            _write_result(job_id, description)
                    else:
                        stats["no_match"] += 1

        await asyncio.gather(*(handle(key, pairs) for key, pairs in by_key.items()))

    print(f"[{provider}] done: {stats}")
    if dry_run:
        print("  (dry-run: no DB writes made)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", required=True, choices=list(PROVIDER_CONFIG.keys()))
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.provider, args.limit, args.dry_run, args.offset))
