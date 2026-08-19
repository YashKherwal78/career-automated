"""
Scans the mailbox for job-alert emails from a known sender allowlist and runs
every extracted lead through the ingestion pipeline in dry-run mode by
default. Counterpart to run_google_forms_batch.py for the email source --
scan_job_alerts() previously had no entry point of any kind, so the entire
Gmail ingestion path was unreachable outside of tests.

Usage:
    python scripts/run_gmail_job_alert_scan.py --user-id <uuid> [--live]
        [--since-days 3] [--sender jobs-noreply@linkedin.com ...]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ingestion.email_extractor import scan_job_alerts, DEFAULT_SENDER_ALLOWLIST
from src.ingestion.pipeline import run_lead


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--live", action="store_true", help="Submit for real (default: dry-run)")
    parser.add_argument("--since-days", type=int, default=3, help="How far back to scan (default: 3)")
    parser.add_argument(
        "--sender", action="append", dest="senders", default=None,
        help=f"Sender to scan; repeatable. Default: {', '.join(DEFAULT_SENDER_ALLOWLIST)}",
    )
    args = parser.parse_args()

    leads = scan_job_alerts(sender_allowlist=args.senders, since_days=args.since_days)
    print(f"Found {len(leads)} job leads in the last {args.since_days} day(s)")

    for lead in leads:
        outcome = run_lead(lead, user_id=args.user_id, test_mode=not args.live)
        print(f"{outcome['status']:<20} {lead.company} / {lead.role}  -> {outcome.get('run_id')}")


if __name__ == "__main__":
    main()
