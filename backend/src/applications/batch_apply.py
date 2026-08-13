"""
Shared batch-apply logic used by both scripts/run_batch_apply.py (CLI) and
the dashboard's "Start Auto Apply" toggle (src/api/routers/applications.py).

Progress is tracked in a module-level dict, not a DB table -- the api
container runs a single uvicorn worker (see Dockerfile CMD), so in-process
state is visible to every request without adding persistence for what is,
today, a single-user deployment.
"""
import json
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.api.db import get_connection, is_postgres
from src.applications.apply_service import apply_to_job
from src.applications.resume_selector import ResumeSelector
from src.referrals.apply_integration import find_and_draft_referral
from src.referrals.hr_pitch_integration import find_and_draft_hr_pitch
from src.resume_intelligence.cover_letter.auto_generate import generate_and_store_cover_letter
from src.system.logger import setup_logger

logger = setup_logger("batch_apply")

_SUPPORTED_PROVIDERS = ("greenhouse", "lever", "ashby")

# user_id -> progress dict, polled by GET /applications/batch-apply/status
_BATCH_STATUS: Dict[str, Dict[str, Any]] = {}


def _row_dict(row, cursor):
    if hasattr(row, "keys"):
        return dict(row)
    if isinstance(row, dict):
        return row
    return dict(zip([col[0] for col in cursor.description], row))


def get_candidate_jobs(conn, user_id: str, min_score: int, limit: Optional[int] = None):
    """Matched, active, dispatcher-supported jobs not yet attempted for this user.

    _ADAPTER_REGISTRY in dispatcher.py lists 14 connector names, but only
    greenhouse/lever/ashby have actual committed, deployed adapter modules
    (the other 11 are uncommitted local-only stub files, never proven
    against a real ATS) -- restrict to what's actually deployed so a job
    doesn't error out for missing a module instead of really being
    attempted.
    """
    ph = "%s" if is_postgres() else "?"
    placeholders = ",".join([ph] * len(_SUPPORTED_PROVIDERS))
    limit_clause = f"LIMIT {int(limit)}" if limit else ""
    query = f"""
        SELECT n.job_id, n.title, n.provider, n.apply_url, n.location, n.description,
               COALESCE(i.canonical_name, n.company_id) AS canonical_name,
               i.domain AS company_domain,
               s.job_score
        FROM public.user_job_scores s
        JOIN public.normalized_jobs n ON n.job_id = s.job_id
        LEFT JOIN public.company_identities i ON n.company_id = i.company_id
        WHERE s.user_id = {ph}
          AND n.status = 'ACTIVE'
          AND s.job_score >= {ph}
          AND n.apply_url IS NOT NULL AND n.apply_url != ''
          AND n.provider IN ({placeholders})
          AND NOT EXISTS (
              SELECT 1 FROM public.application_packages p
              WHERE p.job_id = n.job_id::uuid AND p.user_id = {ph}::uuid
          )
        ORDER BY s.job_score DESC, n.posted_at DESC
        {limit_clause}
    """
    params = [user_id, min_score, *_SUPPORTED_PROVIDERS, user_id]
    cur = conn.execute(query, tuple(params))
    return [_row_dict(r, cur) for r in cur.fetchall()]


def record_attempt(conn, user_id: str, job_id: str, status: str, result_summary: dict):
    ph = "%s" if is_postgres() else "?"
    conn.execute(
        f"""
        INSERT INTO public.application_packages (user_id, job_id, status, screening_answers)
        VALUES ({ph}::uuid, {ph}::uuid, {ph}, {ph})
        """,
        (user_id, job_id, status, json.dumps(result_summary, default=str)),
    )
    conn.commit()


def get_status(user_id: str) -> Dict[str, Any]:
    return _BATCH_STATUS.get(user_id, {"running": False})


def run_batch(
    user_id: str,
    min_score: int = 70,
    limit: Optional[int] = None,
    delay_seconds: float = 8.0,
    live: bool = True,
) -> None:
    """Runs synchronously (intended to be invoked via FastAPI BackgroundTasks,
    which offloads sync callables to a threadpool -- same pattern the single-
    job /apply endpoint already relies on for its own Playwright run)."""
    test_mode = not live

    # Fail fast on a systemic problem (e.g. the resume data directory being
    # empty/unmounted -- confirmed real incident: a bind mount left pointing
    # at a stale, orphaned directory made every single job in a 30+ job
    # batch fail identically with the same RUNNER_ERROR, one at a time,
    # burning the full per-job delay each time before anyone noticed) rather
    # than discovering it 8 seconds and one wasted attempt at a time. This
    # only proves *a* resume resolves, not that every job-specific variant
    # will -- it's a smoke test for "is the data directory even there",
    # not a guarantee.
    try:
        ResumeSelector().get_resume({"job_title": "Software Engineer"}, user_id=user_id)
    except Exception as preflight_err:
        logger.info(f"[batch_apply] user={user_id} aborting before start -- resume preflight failed: {preflight_err}")
        _BATCH_STATUS[user_id] = {
            "running": False,
            "total": 0,
            "completed": 0,
            "submitted": 0,
            "review_required": 0,
            "failed": 0,
            "current_job_title": None,
            "error": f"Aborted before starting: {preflight_err}",
        }
        return

    with get_connection() as conn:
        jobs = get_candidate_jobs(conn, user_id, min_score, limit)
    logger.info(f"[batch_apply] user={user_id} {len(jobs)} candidate jobs (min_score={min_score}, live={live})")

    _BATCH_STATUS[user_id] = {
        "running": True,
        "total": len(jobs),
        "completed": 0,
        "submitted": 0,
        "review_required": 0,
        "failed": 0,
        "current_job_title": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    for i, job in enumerate(jobs):
        job_id = job["job_id"]
        status = _BATCH_STATUS[user_id]
        status["current_job_title"] = job["title"]
        logger.info(
            f"[batch_apply] [{i + 1}/{len(jobs)}] {job['title']!r} ({job['provider']}) "
            f"score={job['job_score']} job_id={job_id}"
        )

        job_row = {
            "job_id": job_id,
            "title": job["title"],
            "canonical_name": job.get("canonical_name", ""),
            "provider": job["provider"],
            "location": job.get("location", ""),
            "apply_url": job["apply_url"],
        }
        record = {
            "job_id": job_id,
            "title": job["title"],
            "provider": job["provider"],
            "job_score": job["job_score"],
            "test_mode": test_mode,
        }
        try:
            result = apply_to_job(job_row, test_mode=test_mode, user_id=user_id)
            record["status"] = result.status
            record["really_submitted"] = bool(result.really_submitted)
            record["failure_reason"] = result.failure_reason

            if result.status == "COMPLETED" and result.really_submitted:
                db_status = "SUBMITTED"
                status["submitted"] += 1
            elif result.status == "REVIEW_REQUIRED":
                db_status = "DRAFT"
                status["review_required"] += 1
            else:
                db_status = "DRAFT"
                status["failed"] += 1
            logger.info(
                f"[batch_apply]   -> status={result.status} really_submitted={result.really_submitted} "
                f"reason={result.failure_reason}"
            )
        except Exception as e:
            record["status"] = "RUNNER_ERROR"
            record["error"] = str(e)
            record["traceback"] = traceback.format_exc()
            db_status = "DRAFT"
            status["failed"] += 1
            logger.info(f"[batch_apply]   -> RUNNER_ERROR: {e}")

        try:
            with get_connection() as attempt_conn:
                record_attempt(attempt_conn, user_id, job_id, db_status, record)
        except Exception:
            pass

        if live:
            # Best-effort, non-fatal by design (see apply_integration.py) --
            # a referral-discovery failure must never affect the batch's own
            # progress/results.
            find_and_draft_referral(
                user_id=user_id,
                job_id=job_id,
                job_title=job["title"],
                company_name=job.get("canonical_name", ""),
                job_description=job.get("description") or "",
                company_domain=job.get("company_domain") or "",
            )
            # Second, independent outreach system -- see hr_pitch_integration.py.
            # Runs alongside the cold-referral-ask above, not instead of it.
            find_and_draft_hr_pitch(
                user_id=user_id,
                job_id=job_id,
                job_title=job["title"],
                company_name=job.get("canonical_name", ""),
                job_description=job.get("description") or "",
                company_domain=job.get("company_domain") or "",
                apply_url=job.get("apply_url") or "",
            )

        if db_status == "SUBMITTED":
            # Paid-tier only (gated inside); best-effort, non-fatal, same
            # pattern as the referral draft above -- a cover-letter LLM
            # call failing must never affect a submission that already
            # succeeded. No email available in this worker context (no
            # request/session here), so the FREE_ACCESS_EMAILS comp
            # exemption doesn't apply from this call site -- only the real
            # 'paid' subscription check does.
            generate_and_store_cover_letter(
                user_id=user_id,
                email=None,
                job_id=job_id,
                job_title=job["title"],
                company_name=job.get("canonical_name", ""),
                job_description=job.get("description") or "",
            )

        status["completed"] = i + 1
        if i < len(jobs) - 1:
            time.sleep(delay_seconds)

    _BATCH_STATUS[user_id]["running"] = False
    _BATCH_STATUS[user_id]["current_job_title"] = None
