"""
Thin connective piece wiring a real discovered job (from `normalized_jobs`,
via `RepositoryManager.job.get_job()`) into `ApplicationDispatcher`.

This is the first real automatic entry point for the auto-apply engine —
previously every real submission (this session's Greenhouse/Lever/Ashby
work included) went through manual scratch scripts hardcoding job URLs.
Kept intentionally small: map the job row's field names to what the
dispatcher/adapters expect, pick a resume, dispatch. No new business logic.
"""
from typing import Any, Dict, Optional

from src.system.logger import setup_logger
from src.applications.dispatcher import ApplicationDispatcher
from src.applications.adapters.base_adapter import ApplicationResult
from src.applications.profile import ProfileManager
from src.applications.rag import RAGClient
from src.applications.resume_selector import ResumeSelector
from src.utils.llm_router import LLMRouter

logger = setup_logger("apply_service")


def _map_job_row(job_row: Dict[str, Any]) -> Dict[str, Any]:
    """`repos.job.get_job()` returns `job_id`/`title`/`provider`/
    `canonical_name`; the dispatcher/adapters expect `id`/`job_title`/
    `connector`/`company_name`. Translate field names only — no new data."""
    return {
        "id": job_row.get("job_id"),
        "job_title": job_row.get("title", ""),
        "company_name": job_row.get("canonical_name", ""),
        "connector": (job_row.get("provider") or "").lower().strip(),
        "location": job_row.get("location", ""),
        "apply_url": job_row.get("apply_url", ""),
    }


def apply_to_job(job_row: Dict[str, Any], test_mode: bool = True, user_id: Optional[str] = None) -> ApplicationResult:
    """
    `job_row` is whatever `RepositoryManager.job.get_job(job_id)` returns.
    `test_mode` defaults to True (never clicks final submit) — callers must
    explicitly pass False for a real submission.

    `user_id`, when supplied, makes ResumeSelector prefer the resume this
    specific user actually uploaded over the generic static default -- see
    ResumeSelector.get_resume's docstring. Optional only because a couple of
    call sites (ad hoc scripts/tests) predate multi-tenant resume support;
    every real request-handling caller should pass it.
    """
    mapped_job = _map_job_row(job_row)

    if not mapped_job["apply_url"]:
        return ApplicationResult(status="REVIEW_REQUIRED", failure_reason="Job has no apply_url")
    if not mapped_job["connector"]:
        return ApplicationResult(status="REVIEW_REQUIRED", failure_reason="Job has no provider/connector set")

    resume_path, _role_family = ResumeSelector().get_resume(mapped_job, user_id=user_id)

    profile_manager = ProfileManager()
    rag_client = RAGClient()
    llm_router = LLMRouter()

    dispatcher = ApplicationDispatcher(
        profile_manager=profile_manager,
        rag_client=rag_client,
        llm_router=llm_router,
    )

    logger.info(f"[ApplyService] Dispatching job {mapped_job['id']} ({mapped_job['connector']}) test_mode={test_mode}")
    return dispatcher.dispatch(mapped_job, resume_path, test_mode=test_mode, user_id=user_id)
