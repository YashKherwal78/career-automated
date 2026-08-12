import json
import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.api.db import get_connection, is_postgres
from src.api.dependencies import get_repos
from src.core.repositories.manager import RepositoryManager
from src.applications import captcha_bridge
from src.applications.apply_service import apply_to_job
from src.applications.batch_apply import get_candidate_jobs, get_status, run_batch
from src.applications.profile import ProfileManager
from src.applications.question_engine import QuestionEngine
from src.applications.rag import RAGClient
from src.applications.resume_selector import ResumeSelector
from src.referrals.apply_integration import find_and_draft_referral
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
    background_tasks: BackgroundTasks,
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

    result = apply_to_job(job_row, test_mode=body.test_mode, user_id=current_user.user_id)

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

    if not body.test_mode:
        background_tasks.add_task(
            find_and_draft_referral,
            user_id=current_user.user_id,
            job_id=job_id,
            job_title=job_row.get("title", ""),
            company_name=job_row.get("canonical_name", ""),
            job_description=job_row.get("description") or "",
            company_domain=job_row.get("company_domain") or "",
        )

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
    resume_path, _role_family = ResumeSelector().get_resume({"job_title": job_title}, user_id=current_user.user_id)
    if not os.path.exists(resume_path):
        raise HTTPException(status_code=404, detail="Resume file not found")
    return FileResponse(
        resume_path,
        media_type="application/pdf",
        filename=os.path.basename(resume_path),
    )


class AutoApplyPolicy(BaseModel):
    enabled: bool
    min_score: int = 70


@router.get("/auto-apply-policy")
def get_auto_apply_policy(current_user: CurrentUser = Depends(get_current_user)):
    """Durable on/off state for the dashboard's "Start Auto Apply" toggle --
    previously only lived in frontend useState, so it reset to "off" on
    every page load/reload regardless of whether a run was still going."""
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        cur = conn.execute(
            f"SELECT enabled, minimum_match_score FROM public.user_application_policies WHERE user_id = {ph}::uuid",
            (current_user.user_id,),
        )
        row = cur.fetchone()
    if not row:
        return {"enabled": False, "min_score": 70}
    d = row if isinstance(row, dict) else dict(row)
    return {"enabled": bool(d.get("enabled")), "min_score": d.get("minimum_match_score", 70)}


@router.post("/auto-apply-policy")
def set_auto_apply_policy(
    body: AutoApplyPolicy,
    current_user: CurrentUser = Depends(get_current_user),
):
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        if is_postgres():
            conn.execute(
                f"""
                INSERT INTO public.user_application_policies (user_id, enabled, minimum_match_score, updated_at)
                VALUES ({ph}::uuid, {ph}, {ph}, NOW())
                ON CONFLICT (user_id) DO UPDATE
                SET enabled = EXCLUDED.enabled, minimum_match_score = EXCLUDED.minimum_match_score, updated_at = NOW()
                """,
                (current_user.user_id, body.enabled, body.min_score),
            )
        else:
            conn.execute(
                f"""
                INSERT OR REPLACE INTO public.user_application_policies (user_id, enabled, minimum_match_score)
                VALUES ({ph}, {ph}, {ph})
                """,
                (current_user.user_id, body.enabled, body.min_score),
            )
        conn.commit()
    return {"enabled": body.enabled, "min_score": body.min_score}


@router.get("/needs-review")
def needs_review(current_user: CurrentUser = Depends(get_current_user)):
    """Applications that stopped short of submitting -- REVIEW_REQUIRED
    (couldn't confidently finish, or hit a CAPTCHA), FAILED, or
    RUNNER_ERROR -- with the actual reason, so a batch run's blockers are
    visible instead of silently sitting in application_packages."""
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        cur = conn.execute(
            f"""
            SELECT p.job_id, p.status, p.screening_answers, p.created_at, n.apply_url
            FROM public.application_packages p
            LEFT JOIN public.normalized_jobs n ON n.job_id = REPLACE(p.job_id::text, '-', '')
            WHERE p.user_id = {ph}::uuid AND p.status != 'SUBMITTED'
            ORDER BY p.created_at DESC
            LIMIT 100
            """,
            (current_user.user_id,),
        )
        rows = cur.fetchall()

    items = []
    for r in rows:
        d = r if isinstance(r, dict) else dict(r)
        answers = d.get("screening_answers")
        if isinstance(answers, str):
            try:
                answers = json.loads(answers)
            except Exception:
                answers = {}
        answers = answers or {}
        items.append({
            "job_id": str(d.get("job_id")),
            "title": answers.get("title", ""),
            "provider": answers.get("provider", ""),
            "job_score": answers.get("job_score"),
            "status": answers.get("status", d.get("status")),
            "reason": answers.get("failure_reason") or answers.get("error") or "",
            "created_at": str(d.get("created_at")),
            "apply_url": d.get("apply_url") or "",
        })
    return {"items": items}


@router.get("/captcha/active")
def get_active_captcha(current_user: CurrentUser = Depends(get_current_user)):
    """Polled by the dashboard to discover "is a background run of mine
    currently stuck on a CAPTCHA right now" without already knowing a
    session_id."""
    session_id = captcha_bridge.get_active_session_id_for_user(current_user.user_id)
    if not session_id:
        return {"active": False}
    session = captcha_bridge.get_session(session_id)
    return {"active": True, "session_id": session_id, "job_id": session.get("job_id") if session else None}


def _require_own_session(session_id: str, current_user: CurrentUser):
    session = captcha_bridge.get_session(session_id)
    if not session or session.get("user_id") != current_user.user_id:
        raise HTTPException(status_code=404, detail="No active captcha session")


@router.get("/captcha/{session_id}/screenshot")
def captcha_screenshot(session_id: str, current_user: CurrentUser = Depends(get_current_user)):
    _require_own_session(session_id, current_user)
    png = captcha_bridge.request_screenshot(session_id)
    if png is None:
        raise HTTPException(status_code=504, detail="Screenshot timed out")
    return Response(content=png, media_type="image/png")


class CaptchaClick(BaseModel):
    x: float
    y: float


@router.post("/captcha/{session_id}/click")
def captcha_click(session_id: str, body: CaptchaClick, current_user: CurrentUser = Depends(get_current_user)):
    _require_own_session(session_id, current_user)
    ok = captcha_bridge.request_click(session_id, body.x, body.y)
    return {"ok": ok}


@router.post("/captcha/{session_id}/resolved")
def captcha_resolved(session_id: str, current_user: CurrentUser = Depends(get_current_user)):
    _require_own_session(session_id, current_user)
    captcha_bridge.signal_resolved(session_id)
    return {"ok": True}


@router.post("/captcha/{session_id}/skip")
def captcha_skip(session_id: str, current_user: CurrentUser = Depends(get_current_user)):
    _require_own_session(session_id, current_user)
    captcha_bridge.signal_skip(session_id)
    return {"ok": True}
