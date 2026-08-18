import os
from typing import Any, Dict

from src.applications.adapters.base_adapter import BaseAdapter, ApplicationResult, derive_diagnosis
from src.applications.browser_launcher import LaunchedBrowser
from src.applications.handlers.google_forms import GoogleFormsHandler
from src.system.logger import setup_logger

logger = setup_logger("google_forms_adapter")


class GoogleFormsAdapter(BaseAdapter):
    def __init__(self, profile_manager=None, rag_client=None, llm_router=None):
        self.profile_manager = profile_manager
        self.rag_client = rag_client
        self.llm_router = llm_router

    def apply(self, job: Dict[str, Any], resume_path: str, profile_manager: Any, test_mode: bool = False, user_id: str = None) -> ApplicationResult:
        logger.info(f"[GoogleFormsAdapter] Launching browser for Job: {job.get('id')} - {job.get('company_name')}")

        execution_dir = job.get("execution_dir") or f"executions/job_{job.get('id')}"
        os.makedirs(execution_dir, exist_ok=True)

        with LaunchedBrowser() as lb:
            page = lb.page
            page.goto(job.get("apply_url") or job.get("job_url"), timeout=30000)

            handler = GoogleFormsHandler(
                page=page,
                job_title=job.get("job_title", ""),
                company_name=job.get("company_name", ""),
                location=job.get("location", ""),
                resume_path=resume_path,
                test_mode=test_mode,
                execution_dir=execution_dir,
                profile_manager=profile_manager or self.profile_manager,
                rag_client=self.rag_client,
                llm_client=self.llm_router,
                company_context=job.get("company_context", ""),
                user_id=user_id,
                job_id=job.get("id"),
            )

            outcome = handler.execute()
            status = outcome.get("status", "FAILED")
            telemetry = outcome.get("telemetry", {})
            proof = telemetry.get("submission_proof", {})

            # Read the keys the rest of the system actually writes:
            # SubmissionVerifier's proof dict is {url, title, success_text,
            # error_text, ...} (verifier.py:21) and really_submitted is set on
            # telemetry itself, not inside proof (base_handler.py:842) -- so
            # confirmation_url/screenshot_path/really_submitted have to come
            # from there, and submitted_answers from the interaction log the
            # way every other adapter builds it (filled_fields is a fixed
            # bool map of ATS-standard fields, which a Google Form has none of).
            interactions = telemetry.get("interaction_log", [])
            answers = {i.get("Question"): i.get("Expected Value") for i in interactions if i.get("Verification Result")}
            really_submitted = telemetry.get("really_submitted", False)

            screenshot_path = os.path.join(execution_dir, "final_state.png")
            try:
                page.screenshot(path=screenshot_path)
            except Exception:
                screenshot_path = ""

            return ApplicationResult(
                status=status,
                confirmation_url=proof.get("url", "") if really_submitted else "",
                screenshot_path=screenshot_path,
                submitted_answers=answers,
                failure_reason=derive_diagnosis(telemetry) if status != "COMPLETED" else "",
                really_submitted=really_submitted,
            )
