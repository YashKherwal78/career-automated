"""
Health & Observability API
GET /api/v1/health          - system health check
GET /api/v1/health/pipeline - full pipeline funnel metrics
GET /api/v1/health/connectors - per-ATS connector reliability
GET /api/v1/health/coverage   - top company coverage report
"""
import time
from fastapi import APIRouter
from src.api.db import get_connection

router = APIRouter()


def _q(conn, sql, params=None):
    r = conn.execute(sql, params or []).fetchone()
    return dict(r) if r else {}


def _ql(conn, sql, params=None):
    return [dict(r) for r in conn.execute(sql, params or []).fetchall()]


@router.get("")
def health_check():
    """Basic health probe for Railway / uptime monitors."""
    try:
        conn = get_connection()
        cnt = _q(conn, "SELECT COUNT(*) cnt FROM normalized_jobs")["cnt"]
        conn.close()
        return {"status": "ok", "jobs": cnt, "ts": int(time.time())}
    except Exception as e:
        return {"status": "error", "detail": str(e), "ts": int(time.time())}


@router.get("/pipeline")
def pipeline_metrics():
    """Full pipeline funnel: Discovery → Verification → Crawl → Jobs."""
    conn = get_connection()
    try:
        funnel = {
            "companies_discovered": _q(conn, "SELECT COUNT(*) cnt FROM company_identities")["cnt"],
            "ats_registry_total": _q(conn, "SELECT COUNT(*) cnt FROM ats_registry")["cnt"],
            "ats_registry_active": _q(conn, "SELECT COUNT(*) cnt FROM ats_registry WHERE status = 'ACTIVE'")["cnt"],
            "ats_registry_needs_review": _q(conn, "SELECT COUNT(*) cnt FROM ats_registry WHERE status = 'NEEDS_REVIEW'")["cnt"],
            "ats_registry_retired": _q(conn, "SELECT COUNT(*) cnt FROM ats_registry WHERE status = 'RETIRED'")["cnt"],
            "companies_crawled": _q(conn, "SELECT COUNT(*) cnt FROM ats_registry WHERE last_successful_crawl IS NOT NULL")["cnt"],
            "companies_never_crawled": _q(conn, "SELECT COUNT(*) cnt FROM ats_registry WHERE status = 'ACTIVE' AND last_successful_crawl IS NULL")["cnt"],
            "jobs_total": _q(conn, "SELECT COUNT(*) cnt FROM normalized_jobs")["cnt"],
            "jobs_active": _q(conn, "SELECT COUNT(*) cnt FROM normalized_jobs WHERE status = 'ACTIVE'")["cnt"],
        }

        # Jobs added in last 24h / 7d
        now = time.time()
        funnel["jobs_last_24h"] = _q(conn,
            "SELECT COUNT(*) cnt FROM normalized_jobs WHERE created_at > %s",
            [now - 86400])["cnt"]
        funnel["jobs_last_7d"] = _q(conn,
            "SELECT COUNT(*) cnt FROM normalized_jobs WHERE created_at > %s",
            [now - 604800])["cnt"]

        # Companies with jobs breakdown
        per_company = _ql(conn, """
            SELECT n.company_id, a.ats_type, COUNT(*) job_count,
                   a.last_successful_crawl, a.failure_count, a.status as ats_status
            FROM normalized_jobs n
            LEFT JOIN ats_registry a ON a.company_id = n.company_id
            GROUP BY n.company_id, a.ats_type, a.last_successful_crawl,
                     a.failure_count, a.status
            ORDER BY job_count DESC
        """)

        # Workers (heartbeats)
        workers = []
        try:
            workers = _ql(conn, "SELECT * FROM worker_states ORDER BY last_heartbeat DESC LIMIT 20")
        except Exception:
            pass

        # Queue depths
        queues = []
        try:
            queues = _ql(conn, """
                SELECT queue_name, status, COUNT(*) cnt
                FROM local_queues
                GROUP BY queue_name, status
                ORDER BY queue_name, status
            """)
        except Exception:
            pass

        return {
            "ts": int(time.time()),
            "funnel": funnel,
            "per_company": per_company,
            "workers": workers,
            "queues": queues,
        }
    finally:
        conn.close()


@router.get("/connectors")
def connector_metrics():
    """Per-ATS connector reliability stats."""
    conn = get_connection()
    try:
        ats_stats = _ql(conn, """
            SELECT
                ats_type,
                COUNT(*) total_companies,
                SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) active,
                SUM(CASE WHEN last_successful_crawl IS NOT NULL THEN 1 ELSE 0 END) crawled,
                SUM(CASE WHEN failure_count > 0 THEN 1 ELSE 0 END) has_failures,
                AVG(failure_count) avg_failures,
                MAX(last_successful_crawl) most_recent_crawl
            FROM ats_registry
            GROUP BY ats_type
            ORDER BY total_companies DESC
        """)

        jobs_per_ats = _ql(conn, """
            SELECT a.ats_type, COUNT(*) job_count, COUNT(DISTINCT n.company_id) companies_with_jobs
            FROM normalized_jobs n
            JOIN ats_registry a ON a.company_id = n.company_id
            GROUP BY a.ats_type
            ORDER BY job_count DESC
        """)

        jobs_map = {r["ats_type"]: r for r in jobs_per_ats}

        result = []
        for s in ats_stats:
            ats = s["ats_type"]
            crawl_rate = round(s["crawled"] / s["total_companies"] * 100, 1) if s["total_companies"] else 0
            j = jobs_map.get(ats, {})
            result.append({
                "ats_type": ats,
                "total_companies": s["total_companies"],
                "active": s["active"],
                "crawled": s["crawled"],
                "crawl_success_rate_pct": crawl_rate,
                "avg_failures": round(float(s["avg_failures"] or 0), 2),
                "job_count": j.get("job_count", 0),
                "companies_with_jobs": j.get("companies_with_jobs", 0),
                "avg_jobs_per_company": round(j.get("job_count", 0) / j.get("companies_with_jobs", 1), 1) if j.get("companies_with_jobs") else 0,
                "most_recent_crawl": s["most_recent_crawl"],
            })

        return {"ts": int(time.time()), "connectors": result}
    finally:
        conn.close()


@router.get("/coverage")
def coverage_report():
    """Top company coverage — which are tracked, which are missing."""
    TOP_COMPANIES = [
        "google", "microsoft", "apple", "amazon", "meta", "netflix", "nvidia",
        "salesforce", "adobe", "oracle", "uber", "airbnb", "stripe", "figma",
        "notion", "linear", "discord", "coinbase", "openai", "anthropic",
        "databricks", "snowflake", "atlassian", "zoom", "dropbox", "lyft",
        "doordash", "instacart", "robinhood", "brex", "ramp", "plaid", "gusto",
        "rippling", "airtable", "webflow", "retool", "vercel", "hashicorp",
        "gitlab", "github", "mongodb", "datadog", "pagerduty", "twilio",
        "sendgrid", "segment", "amplitude", "mixpanel", "hubspot",
    ]

    conn = get_connection()
    try:
        # Check registry
        registry = {r["company_id"]: r for r in _ql(conn, "SELECT company_id, ats_type, status FROM ats_registry")}
        # Check jobs
        job_counts = {r["company_id"]: r["cnt"] for r in _ql(conn, "SELECT company_id, COUNT(*) cnt FROM normalized_jobs GROUP BY company_id")}

        companies = []
        tracked = 0
        has_jobs = 0
        for cid in TOP_COMPANIES:
            reg = registry.get(cid)
            jobs = job_counts.get(cid, 0)
            if reg:
                tracked += 1
            if jobs > 0:
                has_jobs += 1
            companies.append({
                "company": cid,
                "in_registry": bool(reg),
                "ats_type": reg["ats_type"] if reg else None,
                "ats_status": reg["status"] if reg else None,
                "job_count": jobs,
                "status": "✅" if jobs > 0 else ("⚠️" if reg else "❌"),
            })

        return {
            "ts": int(time.time()),
            "summary": {
                "total_checked": len(TOP_COMPANIES),
                "in_registry": tracked,
                "has_jobs": has_jobs,
                "coverage_pct": round(has_jobs / len(TOP_COMPANIES) * 100, 1),
            },
            "companies": companies,
        }
    finally:
        conn.close()
