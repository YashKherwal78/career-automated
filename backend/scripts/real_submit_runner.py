"""
Parameterized submission runner for the autonomous session's Priority 1
(prove at least one real, confirmed submission through Greenhouse or Ashby).

Replaces the one-off `scratch_real_submit.py` (kept in place, not deleted) with
something re-runnable across jobs and both ATSs, and with the session guardrails
enforced in code rather than by remembering to be careful:

  * test_mode defaults to True. Going live requires an explicit --live flag.
  * Live (non-test_mode) submissions are hard-capped at MAX_LIVE_SUBMISSIONS
    per session, tracked in a counter file on disk so the cap survives across
    separate invocations of this script. The runner refuses to launch a live
    run once the cap is reached.
  * Every attempt writes a full evidence bundle to executions/<run_id>/:
    result.json, the handler's screenshots, and (on failure) a DOM snapshot for
    the root-cause-analysis pass the brief requires after 3 failed attempts.

Usage:
    python scripts/real_submit_runner.py --url <job_url> --ats ashby \
        --company "CertifyOS" --title "AI Intern" --location "Pune, India"

    # add --live to actually click Submit
"""
import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_BACKEND, "..", ".env"))

MAX_LIVE_SUBMISSIONS = 5
_COUNTER_PATH = os.path.join(_BACKEND, "executions", ".live_submission_count")


def _live_count() -> int:
    try:
        with open(_COUNTER_PATH) as f:
            return int(f.read().strip() or 0)
    except Exception:
        return 0


def _bump_live_count() -> int:
    n = _live_count() + 1
    os.makedirs(os.path.dirname(_COUNTER_PATH), exist_ok=True)
    with open(_COUNTER_PATH, "w") as f:
        f.write(str(n))
    return n


def _handler_class(ats: str):
    ats = ats.lower()
    if ats == "greenhouse":
        from src.applications.handlers.greenhouse import GreenhouseHandler
        return GreenhouseHandler
    if ats == "ashby":
        from src.applications.handlers.ashby import AshbyHandler
        return AshbyHandler
    # Lever is deliberately excluded from this session's live-submission goal:
    # it has a confirmed hard-blocking interactive hCaptcha. Attempting it here
    # would burn attempts against a known wall. It stays reachable through the
    # normal dispatcher; it is only barred from THIS runner.
    raise SystemExit(f"unsupported/out-of-scope ats for this runner: {ats}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--ats", required=True, choices=["greenhouse", "ashby"])
    ap.add_argument("--company", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--location", default="Remote")
    ap.add_argument("--resume", default="data/Resume_aiml.pdf")
    ap.add_argument("--live", action="store_true",
                    help="actually click Submit (otherwise test_mode dry run)")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()

    test_mode = not args.live
    if args.live:
        used = _live_count()
        if used >= MAX_LIVE_SUBMISSIONS:
            raise SystemExit(
                f"REFUSING: live submission cap reached ({used}/{MAX_LIVE_SUBMISSIONS}). "
                "This cap is a session guardrail — do not raise it without the user."
            )
        print(f"[guardrail] live submission {used + 1}/{MAX_LIVE_SUBMISSIONS}")

    run_id = args.run_id or f"{args.ats}_{args.company.lower().replace(' ', '')}_{'live' if args.live else 'dry'}"
    out_dir = os.path.join(_BACKEND, "executions", run_id)
    os.makedirs(out_dir, exist_ok=True)

    from src.applications.profile import ProfileManager
    from src.applications.rag import RAGClient
    from src.utils.llm_router import LLMRouter
    from src.applications.browser_launcher import LaunchedBrowser

    resume_path = args.resume if os.path.isabs(args.resume) else os.path.join(_BACKEND, args.resume)
    if not os.path.exists(resume_path):
        raise SystemExit(f"resume not found: {resume_path}")

    record = {
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "url": args.url,
        "ats": args.ats,
        "company": args.company,
        "title": args.title,
        "location": args.location,
        "test_mode": test_mode,
        "resume": resume_path,
    }

    handler_cls = _handler_class(args.ats)
    try:
        with LaunchedBrowser() as lb:
            page = lb.page
            page.goto(args.url, timeout=45000)
            page.wait_for_timeout(2000)
            handler = handler_cls(
                page=page,
                job_title=args.title,
                company_name=args.company,
                location=args.location,
                resume_path=resume_path,
                test_mode=test_mode,
                execution_dir=out_dir,
                profile_manager=ProfileManager(),
                rag_client=RAGClient(),
                llm_client=LLMRouter(),
                company_context="",
            )
            result = handler.execute()
            try:
                page.screenshot(path=os.path.join(out_dir, "final_state.png"), full_page=True)
                # DOM snapshot is the raw input for the root-cause-analysis pass
                # the brief mandates after 3 failed attempts on the same field.
                with open(os.path.join(out_dir, "final_dom.html"), "w") as f:
                    f.write(page.content())
            except Exception:
                pass
        record["result"] = result
    except Exception as e:
        record["result"] = {"status": "RUNNER_ERROR", "error": str(e)}
        record["traceback"] = traceback.format_exc()

    telemetry = (record.get("result") or {}).get("telemetry", {}) or {}
    record["finished_at"] = datetime.now(timezone.utc).isoformat()
    record["status"] = (record.get("result") or {}).get("status")
    # status alone is ambiguous: test_mode dry runs also reach COMPLETED without
    # ever clicking submit. really_submitted is the only trustworthy signal.
    record["really_submitted"] = bool(telemetry.get("really_submitted"))
    record["submission_proof"] = telemetry.get("submission_proof")
    record["missing_fields"] = telemetry.get("missing_fields")

    if args.live and record["really_submitted"]:
        record["live_submission_index"] = _bump_live_count()

    with open(os.path.join(out_dir, "result.json"), "w") as f:
        json.dump(record, f, indent=2, default=str)

    print("\n=== RESULT ===")
    print("status:            ", record["status"])
    print("really_submitted:  ", record["really_submitted"])
    print("proof:             ", json.dumps(record["submission_proof"], default=str)[:600])
    print("missing_fields:    ", record["missing_fields"])
    for i in telemetry.get("interaction_log", []) or []:
        print("  ", "OK  " if i.get("Verification Result") else "FAIL",
              str(i.get("Question"))[:70], "->", str(i.get("Expected Value"))[:50])
    if record.get("result", {}).get("error"):
        print("error:", record["result"]["error"])
    print("evidence:          ", out_dir)


if __name__ == "__main__":
    main()
