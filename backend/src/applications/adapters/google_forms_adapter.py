import os
from typing import Any, Dict, Tuple

from src.applications.adapters.base_adapter import BaseAdapter, ApplicationResult, derive_diagnosis
from src.applications.browser_launcher import LaunchedBrowser
from src.applications.handlers.google_forms import GoogleFormsHandler
from src.applications import google_session
from src.ingestion.job_lead import JobLead
from src.ingestion.jd_enrichment import enrich_with_web_search
from src.system.logger import setup_logger

logger = setup_logger("google_forms_adapter")


def _is_google_signin_page(page) -> bool:
    """A sign-in-gated Google Form redirects the browser to
    accounts.google.com before any form content ever loads -- checked via
    URL/title only (no locator reads), so this is cheap and can't itself
    time out or misfire on a slow-rendering but perfectly normal form."""
    try:
        if "accounts.google.com" in (page.url or "").lower():
            return True
        title = (page.title() or "").lower()
        return "sign in" in title and "google" in title
    except Exception:
        return False

# Match pipeline.EXECUTIONS_DIR: backend/executions, resolved absolutely from
# this file rather than from the process's cwd. A relative "executions/job_x"
# fallback scattered audit directories wherever the caller happened to be.
# backend/src/applications/adapters/ -> ../../../ is backend/.
_EXECUTIONS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "executions")
)


class GoogleFormsAdapter(BaseAdapter):
    def __init__(self, profile_manager=None, rag_client=None, llm_router=None):
        self.profile_manager = profile_manager
        self.rag_client = rag_client
        self.llm_router = llm_router

    # ------------------------------------------------------------------
    # JD enrichment (spec §2): DB match -> form description -> web search
    # ------------------------------------------------------------------

    def resolve_jd(self, job: Dict[str, Any], handler: GoogleFormsHandler) -> Tuple[str, str]:
        """Returns (jd_text, jd_source) for this application.

        The three-step chain in the spec was, until now, broken at every
        joint: read_form_description() had no caller anywhere in the
        codebase, the ingestion pipeline skipped the web-search fallback for
        google_forms leads on the assumption that the form description
        covered it, and even a successful DB match died here because this
        adapter only read job["company_context"] -- a key nothing ever set --
        and never job["description"], which is what the pipeline actually
        populates. The net effect was that a Google Form application had NO
        job description context at all, no matter which step succeeded.

        Ordering is load-bearing: each step is only attempted when the
        previous one came up empty, so the paid/rate-limited web search
        (step 3) costs nothing on the common path, and reading the form's own
        heading (step 2) costs nothing at all because the browser is already
        sitting on the form.
        """
        db_jd = (job.get("description") or "").strip()
        if db_jd:
            return db_jd, "db_match"

        try:
            form_jd = (handler.read_form_description() or "").strip()
        except Exception as e:
            logger.info(f"[GoogleFormsAdapter] read_form_description failed: {e}")
            form_jd = ""
        if form_jd:
            return form_jd, "form_description"

        company = job.get("company_name", "") or ""
        role = job.get("job_title", "") or ""
        if not (company or role):
            return "", "none"

        # enrich_with_web_search only reads company/role/jd_excerpt off the
        # lead; source/source_ref are carried for logging symmetry only.
        lead = JobLead(
            company=company, role=role,
            apply_link=job.get("apply_url") or job.get("job_url") or "",
            location=job.get("location", ""), jd_excerpt=None,
            source="screenshot", source_ref=str(job.get("id") or ""),
        )
        try:
            enriched = enrich_with_web_search(lead)
        except Exception as e:
            logger.info(f"[GoogleFormsAdapter] web-search enrichment failed: {e}")
            return "", "none"

        if enriched.jd_excerpt:
            return enriched.jd_excerpt, "web_search"
        return "", "none"

    def apply(self, job: Dict[str, Any], resume_path: str, profile_manager: Any, test_mode: bool = False, user_id: str = None) -> ApplicationResult:
        logger.info(f"[GoogleFormsAdapter] Launching browser for Job: {job.get('id')} - {job.get('company_name')}")

        execution_dir = job.get("execution_dir") or os.path.join(_EXECUTIONS_DIR, f"job_{job.get('id')}")
        os.makedirs(execution_dir, exist_ok=True)

        saved_session = google_session.get_session(user_id)

        with LaunchedBrowser(storage_state=saved_session) as lb:
            page = lb.page
            try:
                page.goto(job.get("apply_url") or job.get("job_url"), timeout=30000)

                if _is_google_signin_page(page):
                    # No amount of retrying fixes this without the
                    # candidate signing in -- surface it as REVIEW_REQUIRED
                    # with a reason that tells them exactly what to do,
                    # rather than falling through into a handler that would
                    # just find zero questions and fail opaquely.
                    if saved_session:
                        # The session we loaded didn't actually sign us in
                        # (expired, revoked, or invalidated by a password
                        # change) -- clear it so Settings shows "not
                        # connected" instead of a connection that silently
                        # stopped working.
                        google_session.delete_session(user_id)
                        reason = (
                            "Your connected Google session expired — reconnect it in "
                            "Settings, then this application will go through on the next run."
                        )
                    else:
                        reason = (
                            "This form requires signing in with your Google account — "
                            "connect it once in Settings, then this application will go "
                            "through on the next run."
                        )
                    logger.info(f"[GoogleFormsAdapter] Sign-in gate hit for job {job.get('id')} (had_saved_session={bool(saved_session)}).")
                    screenshot_path = os.path.join(execution_dir, "google_signin_gate.png")
                    try:
                        page.screenshot(path=screenshot_path)
                    except Exception:
                        screenshot_path = ""
                    return ApplicationResult(
                        status="REVIEW_REQUIRED",
                        screenshot_path=screenshot_path,
                        submitted_answers={},
                        failure_reason=reason,
                    )

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
                    company_context="",
                    user_id=user_id,
                    job_id=job.get("id"),
                )

                # Resolved after construction rather than before, because
                # step 2 needs a handler sitting on the loaded form to read
                # the description off. QuestionEngine's freeform
                # company_context is the right destination: it's already the
                # "background prose about this role/employer" slot the
                # motivation-question prompt folds in (question_engine.py:1216),
                # so nothing about QuestionEngine's signature -- shared with
                # 15 other handlers -- has to change.
                jd_text, jd_source = self.resolve_jd(job, handler)
                if jd_text:
                    handler.engine.company_context = jd_text
                logger.info(f"[GoogleFormsAdapter] jd_source={jd_source} ({len(jd_text)} chars)")

                outcome = handler.execute()
                status = outcome.get("status", "FAILED")
                telemetry = outcome.get("telemetry", {})
                telemetry["jd_source"] = jd_source
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
                    jd_source=jd_source,
                )

            except Exception as e:
                # Without this, a dead forms.gle link (page.goto raising) escaped
                # all the way to the dispatcher's catch-all, which produces a bare
                # "Unhandled Adapter Exception" with no screenshot and no
                # diagnosis -- nothing a human reviewer could act on. Same shape
                # as LeverAdapter's guard.
                logger.info(f"[GoogleFormsAdapter] Exception: {e}")
                screenshot_path = os.path.join(execution_dir, "error_state.png")
                try:
                    page.screenshot(path=screenshot_path)
                except Exception:
                    screenshot_path = ""

                return ApplicationResult(
                    status="FAILED",
                    confirmation_url="",
                    screenshot_path=screenshot_path,
                    submitted_answers={},
                    failure_reason=str(e),
                )
