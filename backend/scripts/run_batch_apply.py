"""
Batch auto-apply runner: pulls a user's real matched jobs from
user_job_scores (populated by JobScoringWorker against the live matching
logic) and submits them through the existing ApplicationDispatcher, one job
at a time.

This reuses apply_service.apply_to_job()/ApplicationDispatcher as-is — no
new matching or ATS-handling logic. It only adds the batch/queue layer that
was missing: candidate selection, dedup, rate limiting, and an evidence
trail, following the same guardrail convention as scripts/real_submit_runner.py:

  * test_mode defaults to True. Going live requires an explicit --live flag.
  * Every attempt is recorded in public.application_packages so a re-run
    never re-applies to a job already attempted for this user.
  * Every attempt writes a result record to executions/batch_apply_<run_id>/.
  * A delay between submissions (--delay-seconds) avoids hammering ATS
    sites back-to-back.

Usage:
    python3 scripts/run_batch_apply.py --user-id <uuid> --min-score 70
    python3 scripts/run_batch_apply.py --user-id <uuid> --min-score 70 --live --limit 5
"""
import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.db import get_connection, is_postgres
from src.applications.apply_service import apply_to_job

_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _row_dict(row, cursor):
    if hasattr(row, "keys"):
        return dict(row)
    if isinstance(row, dict):
        return row
    return dict(zip([col[0] for col in cursor.description], row))


def get_candidate_jobs(conn, user_id: str, min_score: int, limit: int = None):
    """Matched, active, dispatcher-supported jobs not yet attempted for this user.

    _ADAPTER_REGISTRY in dispatcher.py lists 14 connector names, but only
    greenhouse/lever/ashby have actual committed, deployed adapter modules
    (the other 11 are uncommitted local-only stub files, never proven
    against a real ATS) — restrict to what's actually deployed so a job
    doesn't error out for missing a module instead of really being
    attempted.
    """
    supported_providers = ("greenhouse", "lever", "ashby")
    ph = "%s" if is_postgres() else "?"
    placeholders = ",".join([ph] * len(supported_providers))
    limit_clause = f"LIMIT {int(limit)}" if limit else ""
    query = f"""
        SELECT n.job_id, n.title, n.provider, n.apply_url, n.location,
               COALESCE(i.canonical_name, n.company_id) AS canonical_name,
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
    params = [user_id, min_score, *supported_providers, user_id]
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user-id", required=True)
    ap.add_argument("--min-score", type=int, default=70)
    ap.add_argument("--limit", type=int, default=None, help="cap on number of applications this run (omit for uncapped)")
    ap.add_argument("--delay-seconds", type=float, default=8.0)
    ap.add_argument("--live", action="store_true", help="actually submit (otherwise test_mode dry run)")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()

    test_mode = not args.live
    run_id = args.run_id or f"batch_apply_{'live' if args.live else 'dry'}_{int(time.time())}"
    out_dir = os.path.join(_BACKEND, "executions", run_id)
    os.makedirs(out_dir, exist_ok=True)

    with get_connection() as conn:
        jobs = get_candidate_jobs(conn, args.user_id, args.min_score, args.limit)
    print(f"[batch_apply] {len(jobs)} candidate jobs (min_score={args.min_score}, live={args.live})")

    summary = {"submitted": 0, "failed": 0, "review_required": 0, "errored": 0}

    for i, job in enumerate(jobs):
        job_id = job["job_id"]
        print(f"\n[{i+1}/{len(jobs)}] {job['title']!r} ({job['provider']}) score={job['job_score']} job_id={job_id}")
        record = {
            "job_id": job_id,
            "title": job["title"],
            "provider": job["provider"],
            "job_score": job["job_score"],
            "test_mode": test_mode,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            job_row = {
                "job_id": job_id,
                "title": job["title"],
                "canonical_name": job.get("canonical_name", ""),
                "provider": job["provider"],
                "location": job.get("location", ""),
                "apply_url": job["apply_url"],
            }
            result = apply_to_job(job_row, test_mode=test_mode)
            record["status"] = result.status
            record["really_submitted"] = bool(result.really_submitted)
            record["failure_reason"] = result.failure_reason
            record["confirmation_url"] = result.confirmation_url

            if result.status == "COMPLETED" and result.really_submitted:
                db_status = "SUBMITTED"
                summary["submitted"] += 1
            elif result.status == "REVIEW_REQUIRED":
                db_status = "DRAFT"
                summary["review_required"] += 1
            else:
                db_status = "DRAFT"
                summary["failed"] += 1

            print(f"  -> status={result.status} really_submitted={result.really_submitted} reason={result.failure_reason}")
        except Exception as e:
            record["status"] = "RUNNER_ERROR"
            record["error"] = str(e)
            record["traceback"] = traceback.format_exc()
            db_status = "DRAFT"
            summary["errored"] += 1
            print(f"  -> RUNNER_ERROR: {e}")

        record["finished_at"] = datetime.now(timezone.utc).isoformat()
        with open(os.path.join(out_dir, f"{job_id}.json"), "w") as f:
            json.dump(record, f, indent=2, default=str)

        try:
            with get_connection() as attempt_conn:
                record_attempt(attempt_conn, args.user_id, job_id, db_status, record)
        except Exception as e:
            print(f"  -> WARNING: failed to record attempt in application_packages: {e}")

        if i < len(jobs) - 1:
            time.sleep(args.delay_seconds)

    print("\n=== BATCH SUMMARY ===")
    print(json.dumps(summary, indent=2))
    print("evidence dir:", out_dir)


if __name__ == "__main__":
    main()
