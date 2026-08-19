import json
import os
import time
import uuid
import dataclasses

from src.system.logger import setup_logger
from src.ingestion.job_lead import JobLead
from src.ingestion.jd_enrichment import enrich, enrich_with_web_search, already_applied
from src.ingestion.routing import resolve_connector
from src.applications.apply_service import apply_to_job

logger = setup_logger("ingestion_pipeline")

EXECUTIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "executions")


def run_lead(lead: JobLead, user_id: str, test_mode: bool = True) -> dict:
    run_id = f"leads_{lead.source}_{uuid.uuid4().hex[:8]}"

    if already_applied(lead, user_id=user_id):
        logger.info(f"[pipeline] skipping duplicate lead: {lead.company} / {lead.role}")
        return {"run_id": run_id, "status": "SKIPPED_DUPLICATE", "job_lead": dataclasses.asdict(lead)}

    lead = enrich(lead)
    jd_source = "db_match" if lead.jd_excerpt else "none"

    connector, reason = resolve_connector(lead.apply_link)
    if not connector:
        logger.info(f"[pipeline] could not route {lead.apply_link}: {reason}")
        return {
            "run_id": run_id, "status": "REVIEW_REQUIRED",
            "failure_reason": f"Could not route apply link: {reason}",
            "job_lead": dataclasses.asdict(lead), "jd_source": jd_source,
        }

    if not lead.jd_excerpt and connector != "google_forms":
        # Only google_forms gets the form-description fallback (Task 8's
        # GoogleFormsHandler.read_form_description, called from inside
        # GoogleFormsAdapter.apply() -- not reachable from here without
        # opening a browser session redundantly), so any other connector
        # goes straight to the web-search fallback.
        lead = enrich_with_web_search(lead)
        if lead.jd_excerpt:
            jd_source = "web_search"

    job_row = {
        "job_id": str(uuid.uuid4()),
        "title": lead.role,
        "canonical_name": lead.company,
        "provider": connector,
        "location": lead.location or "",
        "apply_url": lead.apply_link,
        "execution_dir": os.path.join(EXECUTIONS_DIR, run_id),
        "description": lead.jd_excerpt or "",
    }

    result = apply_to_job(job_row, test_mode=test_mode, user_id=user_id)

    outcome = {
        "run_id": run_id,
        "started_at": time.time(),
        "company": lead.company,
        "title": lead.role,
        "connector": connector,
        "test_mode": test_mode,
        "status": result.status,
        "really_submitted": result.really_submitted,
        "confirmation_url": result.confirmation_url,
        "screenshot_path": result.screenshot_path,
        "submitted_answers": result.submitted_answers,
        "failure_reason": result.failure_reason,
        "job_lead": dataclasses.asdict(lead),
        "jd_source": jd_source,
    }

    os.makedirs(job_row["execution_dir"], exist_ok=True)
    with open(os.path.join(job_row["execution_dir"], "result.json"), "w") as f:
        json.dump(outcome, f, indent=2, default=str)

    return outcome
