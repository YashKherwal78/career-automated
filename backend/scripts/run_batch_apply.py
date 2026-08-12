"""
Batch auto-apply runner: pulls a user's real matched jobs from
user_job_scores (populated by JobScoringWorker against the live matching
logic) and submits them through the existing ApplicationDispatcher, one job
at a time.

The actual query/apply/record loop lives in src/applications/batch_apply.py
(shared with the dashboard's "Start Auto Apply" toggle, which triggers the
same run_batch() in the background from an API request instead of the CLI).
This script is now a thin arg-parsing wrapper over that, following the same
guardrail convention as scripts/real_submit_runner.py:

  * test_mode defaults to True. Going live requires an explicit --live flag.
  * Every attempt is recorded in public.application_packages so a re-run
    never re-applies to a job already attempted for this user.
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.applications.batch_apply import get_status, run_batch  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user-id", required=True)
    ap.add_argument("--min-score", type=int, default=70)
    ap.add_argument("--limit", type=int, default=None, help="cap on number of applications this run (omit for uncapped)")
    ap.add_argument("--delay-seconds", type=float, default=8.0)
    ap.add_argument("--live", action="store_true", help="actually submit (otherwise test_mode dry run)")
    args = ap.parse_args()

    run_batch(
        user_id=args.user_id,
        min_score=args.min_score,
        limit=args.limit,
        delay_seconds=args.delay_seconds,
        live=args.live,
    )

    print("\n=== BATCH SUMMARY ===")
    print(json.dumps(get_status(args.user_id), indent=2))


if __name__ == "__main__":
    main()
