"""
Liveness preflight for auto-apply targets.

Found during the 2026-08-01 session: `normalized_jobs.status = 'ACTIVE'` is stale
(jobs close without the crawler noticing), and a plain HTTP status check does not
catch it — Ashby is a client-rendered SPA that returns **200 OK** for a removed
job and only renders "Job not found" after hydration. The first dry run of the
session was spent on a dead posting for exactly this reason.

So liveness has to be judged on rendered text, not the HTTP code. This script
renders each URL in a real browser and classifies it LIVE / CLOSED / UNKNOWN so
the submission runner isn't spending attempts on dead postings.

Usage:
    python scripts/check_job_liveness.py <url> [<url> ...]
    python scripts/check_job_liveness.py --from-db --ats ashby --limit 30
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Rendered-text markers. Kept deliberately narrow — a substring like "closed"
# alone would false-positive on job descriptions that merely use the word.
DEAD_MARKERS = [
    "job not found",
    "the job you requested was not found",
    "this job is no longer",
    "no longer accepting applications",
    "position has been filled",
    "job posting is no longer available",
    "this role is no longer open",
    "page not found",
    "404",
]
LIVE_MARKERS = [
    "apply for this job",
    "submit application",
    "application",
    "first name",
    "resume",
]


def classify(text: str) -> str:
    low = " ".join(text.lower().split())
    for m in DEAD_MARKERS:
        if m in low:
            return "CLOSED"
    for m in LIVE_MARKERS:
        if m in low:
            return "LIVE"
    return "UNKNOWN"


def urls_from_db(ats: str, limit: int) -> list[tuple]:
    import sqlite3
    db = os.path.join(_BACKEND, "data", "crm.db")
    con = sqlite3.connect(db)
    q = """select apply_url, title, location, company_id from normalized_jobs
           where provider = ? and status = 'ACTIVE'
             and (lower(title) like '%intern%' or lower(title) like '%new grad%'
                  or lower(title) like '%graduate%' or lower(title) like '%junior%'
                  or lower(title) like '%entry level%' or lower(title) like '%early career%'
                  or lower(title) like '%associate%')
             and (lower(title) like '%engineer%' or lower(title) like '%developer%'
                  or lower(title) like '%software%' or lower(title) like '%data%'
                  or lower(title) like '%ai%' or lower(title) like '%ml%')
           order by posted_at desc limit ?"""
    return con.execute(q, (ats, limit)).fetchall()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="*")
    ap.add_argument("--from-db", action="store_true")
    ap.add_argument("--ats", default="ashby")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if args.from_db:
        rows = urls_from_db(args.ats, args.limit)
    else:
        rows = [(u, "", "", "") for u in args.urls]
    if not rows:
        raise SystemExit("no urls to check")

    from playwright.sync_api import sync_playwright

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for url, title, location, company in rows:
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(2500)
                text = page.locator("body").inner_text()[:6000]
                verdict = classify(text)
            except Exception as e:
                verdict = "UNKNOWN"
                text = f"ERROR: {e}"
            results.append({"url": url, "title": title, "location": location,
                            "company": company, "verdict": verdict})
            print(f"{verdict:8} | {str(title)[:42]:42} | {str(location)[:18]:18} | {url}")
        browser.close()

    if args.out:
        with open(args.out, "w") as f:
            json.dump(results, f, indent=2)
    live = [r for r in results if r["verdict"] == "LIVE"]
    print(f"\nLIVE: {len(live)} / {len(results)}")


if __name__ == "__main__":
    main()
