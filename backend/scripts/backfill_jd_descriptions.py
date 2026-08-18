"""
One-time backfill for jobs stuck with an empty `description`.

Root cause (confirmed via a full DB audit, 2026-08-18): Workday, SmartRecruiters
and iCIMS all already have a working per-job detail-page fetch (added in
af1115e for Workday, and its siblings for the other two) -- but
DefaultFreshnessStrategy.should_sync gates a board's *entire* sync() on a
content-hash of its job-list page. If a company's board hasn't changed since
the fix landed, should_sync returns False and the per-job detail-fetch loop
inside sync() never runs, so jobs normalized before the fix keep their empty
description forever even though the fetch code itself works fine.

Rather than touch the live crawl scheduler's freshness gate (high blast
radius -- it governs every provider, not just these three), this script
calls each connector's existing `_fetch_description` directly against rows
already sitting in normalized_jobs with description IS NULL/''. It reuses
the exact same detail-fetch logic the live crawler would have used --
same URL construction, same Redis cache, same throttle -- just without going
through sync()/should_sync().

For iCIMS/JazzHR/Phenom/Eightfold/Avature, `apply_url` IS (or resolves
directly to) the job detail page URL and is passed straight through, with
the job id read from `raw_payload["id"]`.
For Workday/SmartRecruiters, the tenant/site/company slug + job id are
derived from `apply_url` (verified against real rows: Workday's apply_url is
https://{tenant}.wd{n}.myworkdayjobs.com/{locale}/{site}/job/..., and
SmartRecruiters' is https://jobs.smartrecruiters.com/{slug}/{id}).

Oracle is a genuinely NEW fetch (its connector never had one before this
session): the list endpoint only returns a short marketing blurb
(ShortDescriptionStr), the real JD lives behind
recruitingCEJobRequisitionDetails?expand=all, keyed by requisition id +
site number (both derivable from apply_url, which is
{base}/hcmUI/CandidateExperience/en/sites/{site}/job/{req_id}).

BambooHR/Rippling/join_com also already had a working per-job detail
fetch (5affe1c / 5f57e69) and fit the same per-job-URL pattern as the
providers above -- apply_url + raw_payload["id"]/["idParam"] is enough to
reconstruct the detail call.

Same class of fix still needed but NOT covered by this script (re-fetching
the board's *list* endpoint once and matching by id, not a per-job detail
page -- see backfill_board_wide_descriptions.py for that shape): Personio,
Pinpoint, Recruiterbox, SuccessFactors.

On a successful fetch, this also clears embedding/jd_profile/jd_hash so the
existing EmbeddingBackfillWorker (src/workers/embedding_backfill_worker.py)
naturally re-embeds the job from its real description on its next pass --
no duplicate embedding logic needed here.

Usage:
    python3 scripts/backfill_jd_descriptions.py --provider workday --limit 500
    python3 scripts/backfill_jd_descriptions.py --provider smartrecruiters --limit 500
    python3 scripts/backfill_jd_descriptions.py --provider icims --limit 500
    python3 scripts/backfill_jd_descriptions.py --provider oracle --limit 500
    python3 scripts/backfill_jd_descriptions.py --provider jazzhr --limit 500
    python3 scripts/backfill_jd_descriptions.py --provider phenom --limit 500
    python3 scripts/backfill_jd_descriptions.py --provider eightfold --limit 500
    python3 scripts/backfill_jd_descriptions.py --provider avature --limit 500
    python3 scripts/backfill_jd_descriptions.py --provider bamboohr --limit 500
    python3 scripts/backfill_jd_descriptions.py --provider rippling --limit 500
    python3 scripts/backfill_jd_descriptions.py --provider join_com --limit 500
    python3 scripts/backfill_jd_descriptions.py --provider workday --limit 50 --dry-run
"""
import argparse
import asyncio
import os
import sys
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.db import get_connection, is_postgres  # noqa: E402
from src.discovery.pipeline.http_client import HttpClient  # noqa: E402
from src.discovery.detail_fetch import DetailFetchThrottle  # noqa: E402
from src.discovery.connectors.workday import WorkdayConnector  # noqa: E402
from src.discovery.connectors.smartrecruiters import SmartRecruitersConnector  # noqa: E402
from src.discovery.connectors.icims import iCIMSConnector  # noqa: E402
from src.discovery.connectors.oracle import OracleJSONConnector  # noqa: E402
from src.discovery.connectors.jazzhr import JazzHRConnector  # noqa: E402
from src.discovery.connectors.phenom import PhenomConnector  # noqa: E402
from src.discovery.connectors.eightfold import EightfoldConnector  # noqa: E402
from src.discovery.connectors.avature import AvatureConnector  # noqa: E402
from src.discovery.connectors.bamboohr import BambooHRConnector  # noqa: E402
from src.discovery.connectors.rippling import RipplingConnector  # noqa: E402
from src.discovery.connectors.join_com import JoinComConnector  # noqa: E402

CONCURRENCY = 8
_JOB_URL_ID_HEADERS = {"User-Agent": "Mozilla/5.0"}


def _workday_targets(apply_url: str, raw_payload: dict) -> tuple[str, str] | None:
    """Returns (cxs_base, external_path) or None if apply_url doesn't match
    the expected https://{tenant}.wd{n}.myworkdayjobs.com/{locale}/{site}/job/...
    shape."""
    external_path = raw_payload.get("externalPath") or ""
    if not external_path:
        return None
    parts = urlsplit(apply_url)
    domain = parts.netloc
    path_segments = [p for p in parts.path.split("/") if p]
    if not domain or len(path_segments) < 3 or "myworkdayjobs.com" not in domain:
        return None
    tenant = domain.split(".")[0]
    site = path_segments[1]  # [locale, site, "job", ...]
    return f"https://{domain}/wday/cxs/{tenant}/{site}", external_path


def _smartrecruiters_targets(apply_url: str, raw_payload: dict) -> tuple[str, str] | None:
    """Returns (slug, job_id) from https://jobs.smartrecruiters.com/{slug}/{id}."""
    job_id = str(raw_payload.get("id") or "")
    parts = urlsplit(apply_url)
    path_segments = [p for p in parts.path.split("/") if p]
    if not job_id or len(path_segments) < 2:
        return None
    return path_segments[0], job_id


def _oracle_targets(apply_url: str, raw_payload: dict) -> tuple[str, str, str] | None:
    """Returns (base_url, req_id, site_number) from
    {base}/hcmUI/CandidateExperience/en/sites/{site}/job/{req_id}."""
    req_id = str(raw_payload.get("id") or "")
    parts = urlsplit(apply_url)
    path_segments = [p for p in parts.path.split("/") if p]
    if not req_id or "sites" not in path_segments or not parts.netloc:
        return None
    idx = path_segments.index("sites")
    if idx + 1 >= len(path_segments):
        return None
    site_number = path_segments[idx + 1]
    return f"{parts.scheme}://{parts.netloc}", req_id, site_number


def _job_url_id_targets(apply_url: str, raw_payload: dict) -> tuple[str, str] | None:
    """For connectors whose _fetch_description just needs (job_url, ats_id):
    JazzHR, Phenom, Eightfold, BambooHR (careers_url positionally == job_url)."""
    job_id = str(raw_payload.get("id") or "")
    if not apply_url or not job_id:
        return None
    return apply_url, job_id


def _rippling_targets(apply_url: str, raw_payload: dict) -> tuple[str, str] | None:
    """Returns (slug, ats_id) from https://ats.rippling.com/{slug}/jobs/{uuid}."""
    ats_id = str(raw_payload.get("id") or "")
    parts = urlsplit(apply_url)
    path_segments = [p for p in parts.path.split("/") if p]
    if not ats_id or len(path_segments) < 1:
        return None
    return path_segments[0], ats_id


def _join_com_targets(apply_url: str, raw_payload: dict) -> tuple[str, str] | None:
    """Returns (company_id, id_param) from
    https://join.com/companies/{company_id}/{id_param} -- apply_url is
    already in exactly this shape (verified against real rows)."""
    id_param = str(raw_payload.get("idParam") or "")
    parts = urlsplit(apply_url)
    path_segments = [p for p in parts.path.split("/") if p]
    if not id_param or "companies" not in path_segments:
        return None
    idx = path_segments.index("companies")
    if idx + 1 >= len(path_segments):
        return None
    return path_segments[idx + 1], id_param


async def _fetch_one(provider: str, connector, http_client, throttle, apply_url: str, raw_payload: dict):
    """Returns (description_or_none, url_derived: bool) -- url_derived
    distinguishes "couldn't build a detail URL from this row at all" from
    "built a URL fine but the fetch itself came back empty/non-200", so the
    caller's stats don't lump unrelated failure modes together."""
    if provider == "workday":
        targets = _workday_targets(apply_url, raw_payload)
        if not targets:
            return None, False
        cxs_base, external_path = targets
        return await connector._fetch_description(cxs_base, external_path, http_client, throttle), True
    if provider == "smartrecruiters":
        targets = _smartrecruiters_targets(apply_url, raw_payload)
        if not targets:
            return None, False
        slug, job_id = targets
        return await connector._fetch_description(slug, job_id, http_client, throttle), True
    if provider == "icims":
        if not apply_url:
            return None, False
        return await connector._fetch_description(apply_url, http_client, throttle), True
    if provider == "oracle":
        targets = _oracle_targets(apply_url, raw_payload)
        if not targets:
            return None, False
        base_url, req_id, site_number = targets
        return await connector._fetch_description(base_url, req_id, site_number, http_client, throttle), True
    if provider in ("jazzhr", "phenom", "eightfold"):
        targets = _job_url_id_targets(apply_url, raw_payload)
        if not targets:
            return None, False
        job_url, job_id = targets
        # jazzhr's signature also takes `slug` (unused beyond logging there);
        # pass a harmless placeholder since we don't reconstruct it here.
        if provider == "jazzhr":
            return await connector._fetch_description(http_client, job_url, "backfill", job_id), True
        return await connector._fetch_description(http_client, job_url, job_id), True
    if provider == "avature":
        targets = _job_url_id_targets(apply_url, raw_payload)
        if not targets:
            return None, False
        job_url, job_id = targets
        return await connector._fetch_description(http_client, job_url, _JOB_URL_ID_HEADERS, job_id), True
    if provider == "bamboohr":
        targets = _job_url_id_targets(apply_url, raw_payload)
        if not targets:
            return None, False
        careers_url, job_id = targets
        slug = urlsplit(apply_url).netloc.split(".bamboohr.com")[0]
        return await connector._fetch_description(http_client, careers_url, slug, job_id), True
    if provider == "rippling":
        targets = _rippling_targets(apply_url, raw_payload)
        if not targets:
            return None, False
        slug, ats_id = targets
        return await connector._fetch_description(http_client, slug, ats_id), True
    if provider == "join_com":
        targets = _join_com_targets(apply_url, raw_payload)
        if not targets:
            return None, False
        company_id, id_param = targets
        return await connector._fetch_description(company_id, id_param, http_client, throttle), True
    raise ValueError(f"No backfill strategy for provider={provider!r}")


def _fetch_rows(provider: str, limit: int, offset: int = 0):
    """offset matters: rows that fail to fetch a description stay in the
    WHERE-empty set forever, so LIMIT alone (no offset) would return the
    exact same top rows on every call and the caller would burn requests
    retrying permanently-dead postings in an infinite loop. Callers doing
    a full-backlog sweep MUST advance offset each batch (see
    run_jd_backfill_loop.sh)."""
    import json as _json
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT job_id, apply_url, raw_payload_json FROM normalized_jobs
            WHERE provider = %s AND status = 'ACTIVE'
              AND (description IS NULL OR description = '')
              AND apply_url IS NOT NULL AND apply_url != ''
            ORDER BY normalized_at DESC
            LIMIT %s OFFSET %s
            """ if is_postgres() else
            """
            SELECT job_id, apply_url, raw_payload_json FROM normalized_jobs
            WHERE provider = ? AND status = 'ACTIVE'
              AND (description IS NULL OR description = '')
              AND apply_url IS NOT NULL AND apply_url != ''
            ORDER BY normalized_at DESC
            LIMIT ? OFFSET ?
            """,
            (provider, limit, offset),
        )
        rows = cur.fetchall()
        out = []
        for row in rows:
            d = dict(row) if hasattr(row, "keys") else dict(zip([c[0] for c in cur.description], row))
            try:
                d["raw_payload"] = _json.loads(d.get("raw_payload_json") or "{}")
            except Exception:
                d["raw_payload"] = {}
            out.append(d)
        return out
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
    connector_cls = {
        "workday": WorkdayConnector,
        "smartrecruiters": SmartRecruitersConnector,
        "icims": iCIMSConnector,
        "oracle": OracleJSONConnector,
        "jazzhr": JazzHRConnector,
        "phenom": PhenomConnector,
        "eightfold": EightfoldConnector,
        "avature": AvatureConnector,
        "bamboohr": BambooHRConnector,
        "rippling": RipplingConnector,
        "join_com": JoinComConnector,
    }[provider]
    connector = connector_cls()

    rows = _fetch_rows(provider, limit, offset)
    print(f"[{provider}] {len(rows)} candidate rows (empty description, ACTIVE, has apply_url)")
    if not rows:
        return

    sem = asyncio.Semaphore(CONCURRENCY)
    stats = {"fetched": 0, "empty": 0, "unparseable_url": 0, "fetch_failed": 0, "error": 0}

    async with HttpClient() as http_client:
        throttle = DetailFetchThrottle(requests_per_second=5.0)

        async def handle(row):
            async with sem:
                try:
                    description, url_derived = await _fetch_one(
                        provider, connector, http_client, throttle,
                        row["apply_url"], row["raw_payload"],
                    )
                except Exception as e:
                    stats["error"] += 1
                    print(f"  ERROR job_id={row['job_id']}: {e}")
                    return

                if description is None:
                    stats["unparseable_url" if not url_derived else "fetch_failed"] += 1
                    return
                if not description.strip():
                    stats["empty"] += 1
                    return

                stats["fetched"] += 1
                if not dry_run:
                    _write_result(row["job_id"], description)

        await asyncio.gather(*(handle(r) for r in rows))

    print(f"[{provider}] done: {stats}")
    if dry_run:
        print("  (dry-run: no DB writes made)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--provider", required=True,
        choices=[
            "workday", "smartrecruiters", "icims", "oracle", "jazzhr", "phenom", "eightfold",
            "avature", "bamboohr", "rippling", "join_com",
        ],
    )
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.provider, args.limit, args.dry_run, args.offset))
