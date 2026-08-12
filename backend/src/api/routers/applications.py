import json
import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.api.db import get_connection, is_postgres
from src.api.dependencies import get_repos
from src.core.repositories.manager import RepositoryManager
from src.applications.apply_service import apply_to_job
from src.applications.batch_apply import get_candidate_jobs, get_status, run_batch
from src.applications.profile import ProfileManager
from src.applications.question_engine import QuestionEngine
from src.applications.rag import RAGClient
from src.applications.resume_selector import ResumeSelector
from src.runtime.auth.dependencies import CurrentUser, get_current_user
from src.utils.llm_router import LLMRouter

router = APIRouter()

@router.get("/")
def get_applications(repos = Depends(get_repos)):
    return {"message": "Welcome to applications API"}


class ApplyRequest(BaseModel):
    # Defaults to True (never clicks final submit) — the same safe default
    # as ApplicationDispatcher.dispatch() itself. A real submission requires
    # the caller to explicitly opt in.
    test_mode: bool = True


@router.post("/{job_id}/apply")
def apply_to_job_endpoint(
    job_id: str,
    body: ApplyRequest = ApplyRequest(),
    repos: RepositoryManager = Depends(get_repos),
    current_user: CurrentUser = Depends(get_current_user),
):
    job_row = repos.job.get_job(job_id)
    if not job_row:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Mirrors scripts/run_batch_apply.py's dedup: without this, a page
    # reload resets the frontend's in-memory queue state and a re-click
    # would fire a second real application at the same employer for a job
    # already attempted by this user.
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        cur = conn.execute(
            f"SELECT status FROM public.application_packages WHERE job_id = {ph}::uuid AND user_id = {ph}::uuid",
            (job_id, current_user.user_id),
        )
        existing = cur.fetchone()
        if existing:
            existing_status = existing["status"] if hasattr(existing, "keys") else existing[0]
            raise HTTPException(
                status_code=409,
                detail=f"Already applied to this job (status={existing_status})",
            )

    result = apply_to_job(job_row, test_mode=body.test_mode)

    db_status = (
        "SUBMITTED" if (result.status == "COMPLETED" and result.really_submitted) else "DRAFT"
    )
    with get_connection() as conn:
        conn.execute(
            f"""
            INSERT INTO public.application_packages (user_id, job_id, status, screening_answers)
            VALUES ({ph}::uuid, {ph}::uuid, {ph}, {ph})
            """,
            (current_user.user_id, job_id, db_status, json.dumps(result.submitted_answers or {}, default=str)),
        )
        conn.commit()

    return {
        "status": result.status,
        # The only field that answers "was this actually submitted?" — a
        # dry run (test_mode=True) can reach status="COMPLETED" too, without
        # ever clicking submit, so status alone is not proof of submission.
        "really_submitted": result.really_submitted,
        "confirmation_url": result.confirmation_url,
        "screenshot_path": result.screenshot_path,
        "submitted_answers": result.submitted_answers,
        "failure_reason": result.failure_reason,
    }


class BatchApplyRequest(BaseModel):
    min_score: int = 70
    limit: int | None = None


@router.post("/batch-apply")
def start_batch_apply(
    body: BatchApplyRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(get_current_user),
):
    existing = get_status(current_user.user_id)
    if existing.get("running"):
        raise HTTPException(status_code=409, detail="A batch-apply run is already in progress")

    with get_connection() as conn:
        candidate_count = len(get_candidate_jobs(conn, current_user.user_id, body.min_score, body.limit))

    # Runs in a threadpool after this response is sent (BackgroundTasks'
    # standard behaviour for a sync callable) -- same offload FastAPI
    # already gives the single-job /apply route above for its own
    # Playwright run, just outside the request/response cycle this time so
    # a multi-job run doesn't hold the HTTP connection open for minutes.
    background_tasks.add_task(
        run_batch,
        user_id=current_user.user_id,
        min_score=body.min_score,
        limit=body.limit,
        live=True,
    )
    return {"started": True, "candidate_count": candidate_count}


@router.get("/batch-apply/status")
def batch_apply_status(current_user: CurrentUser = Depends(get_current_user)):
    return get_status(current_user.user_id)


class AutofillQuestion(BaseModel):
    question: str
    field_type: str = "text"
    placeholder: str = ""
    options: list[str] | None = None
    label_text: str = ""
    required: bool = False


class AutofillRequest(BaseModel):
    job_title: str
    company_name: str = ""
    location: str = ""
    questions: list[AutofillQuestion]


@router.post("/autofill")
def autofill_answers(
    body: AutofillRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Answer-generation only -- no browser, no DOM. Built for the browser
    extension (runs in the user's own real Chrome, so it does the DOM
    extraction/filling itself and just needs answers back): reuses the same
    QuestionEngine the Playwright-based auto-apply flow already calls from
    inside base_handler.py, since QuestionEngine.answer() only ever took
    plain extracted data (label/type/options), never a live Page object.
    """
    engine = QuestionEngine(
        profile_manager=ProfileManager(),
        rag_client=RAGClient(),
        llm_client=LLMRouter(),
        company_context=body.company_name,
        job_title=body.job_title,
        job_location=body.location,
    )
    answers = []
    for q in body.questions:
        try:
            answer = engine.answer(
                question=q.question,
                field_type=q.field_type,
                placeholder=q.placeholder,
                options=q.options,
                label_text=q.label_text,
                required=q.required,
            )
        except Exception as e:
            answer = ""
        answers.append(answer)
    return {"answers": answers}


@router.get("/resume-for-job")
def resume_for_job(
    job_title: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Lets the extension fetch the right resume variant for a job (same
    selection logic apply_service uses) to attach via a real file input in
    the user's own browser."""
    resume_path, _role_family = ResumeSelector().get_resume({"job_title": job_title})
    if not os.path.exists(resume_path):
        raise HTTPException(status_code=404, detail="Resume file not found")
    return FileResponse(
        resume_path,
        media_type="application/pdf",
        filename=os.path.basename(resume_path),
    )
