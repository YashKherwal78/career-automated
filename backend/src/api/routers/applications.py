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
from src.applications.rag import get_rag_client
from src.applications.resume_selector import ResumeSelector
from src.referrals.apply_integration import find_and_draft_referral
from src.referrals.hr_pitch_integration import find_and_draft_hr_pitch
from src.resume_intelligence.cover_letter.auto_generate import generate_and_store_cover_letter
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

    # Claims a row up front, atomically, instead of a plain SELECT-then-
    # INSERT-later dedupe check -- the old version checked for an existing
    # row, then ran the (multi-minute) Playwright apply, then inserted
    # afterwards, leaving a window where two near-simultaneous requests for
    # the same job could both pass the check before either insert landed
    # and both go on to really submit. INSERT ... ON CONFLICT DO NOTHING
    # against the unique (user_id, job_id) constraint (migration 037) makes
    # the second concurrent request fail here, before it ever touches
    # Playwright, instead of racing.
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        cur = conn.execute(
            f"""
            INSERT INTO public.application_packages (user_id, job_id, status)
            VALUES ({ph}::uuid, {ph}::uuid, 'PENDING')
            ON CONFLICT (user_id, job_id) DO NOTHING
            RETURNING package_id
            """,
            (current_user.user_id, job_id),
        )
        claimed = cur.fetchone()
        conn.commit()
        if not claimed:
            cur = conn.execute(
                f"SELECT status FROM public.application_packages WHERE job_id = {ph}::uuid AND user_id = {ph}::uuid",
                (job_id, current_user.user_id),
            )
            existing = cur.fetchone()
            existing_status = (existing["status"] if hasattr(existing, "keys") else existing[0]) if existing else "unknown"
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
            UPDATE public.application_packages
            SET status = {ph}, screening_answers = {ph}, updated_at = NOW()
            WHERE user_id = {ph}::uuid AND job_id = {ph}::uuid
            """,
            (db_status, json.dumps(result.submitted_answers or {}, default=str), current_user.user_id, job_id),
        )
        conn.commit()

    if not body.test_mode and db_status == "SUBMITTED":
        # Outreach (and the cover letter below) only fire once the
        # application actually went out -- this used to gate only on
        # `not test_mode`, so a real-mode attempt that ended in
        # REVIEW_REQUIRED/FAILED could still send a cold email referencing
        # an application that was never actually submitted.
        background_tasks.add_task(
            find_and_draft_referral,
            user_id=current_user.user_id,
            job_id=job_id,
            job_title=job_row.get("title", ""),
            company_name=job_row.get("canonical_name", ""),
            job_description=job_row.get("description") or "",
            company_domain=job_row.get("company_domain") or "",
        )
        # Second, independent outreach system -- see hr_pitch_integration.py.
        # Runs alongside the cold-referral-ask above, not instead of it.
        background_tasks.add_task(
            find_and_draft_hr_pitch,
            user_id=current_user.user_id,
            job_id=job_id,
            job_title=job_row.get("title", ""),
            company_name=job_row.get("canonical_name", ""),
            job_description=job_row.get("description") or "",
            company_domain=job_row.get("company_domain") or "",
            apply_url=job_row.get("apply_url") or "",
        )
        # Paid-tier only (gated inside generate_and_store_cover_letter).
        background_tasks.add_task(
            generate_and_store_cover_letter,
            user_id=current_user.user_id,
            email=current_user.email,
            job_id=job_id,
            job_title=job_row.get("title", ""),
            company_name=job_row.get("canonical_name", ""),
            job_description=job_row.get("description") or "",
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

    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        cur = conn.execute(
            f"SELECT apply_mode FROM public.user_application_policies WHERE user_id = {ph}::uuid",
            (current_user.user_id,),
        )
        row = cur.fetchone()
    apply_mode = (row["apply_mode"] if isinstance(row, dict) else (dict(row)["apply_mode"] if row else None)) or "automatic"
    if apply_mode == "assisted":
        # Assisted-mode users never get server-side dispatch -- they work
        # matched jobs themselves via "Open & Autofill" (extension, runs on
        # their own machine/IP). Starting a batch here would silently run
        # Playwright against jobs they expect to handle by hand.
        # 403, not 409 -- start_batch_apply's callers already treat 409
        # ("a run is already in progress") as an idempotent success, so a
        # real policy rejection needs its own status code to be seen at all.
        raise HTTPException(
            status_code=403,
            detail="Auto Apply is set to assisted mode -- switch to automatic mode in preferences to run applications on the server.",
        )

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
        profile_manager=ProfileManager(user_id=current_user.user_id),
        rag_client=get_rag_client(user_id=current_user.user_id),
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
    # 'automatic': runs server-side (batch_apply.run_batch), costs compute,
    # hits the live-view CAPTCHA flow when needed. 'assisted': matched jobs
    # surface an "Open & Autofill" action instead of ever being dispatched
    # server-side -- runs on the user's own machine/IP via the extension.
    apply_mode: str = "automatic"
    # Opt-in checkpoint: pause once, right before the final submit click, and
    # hand the live-view session to the user for a look before it goes out.
    # Built for mobile users (no extension there), but works for anyone.
    confirm_before_submit: bool = False


@router.get("/auto-apply-policy")
def get_auto_apply_policy(current_user: CurrentUser = Depends(get_current_user)):
    """Durable on/off state for the dashboard's "Start Auto Apply" toggle --
    previously only lived in frontend useState, so it reset to "off" on
    every page load/reload regardless of whether a run was still going."""
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        cur = conn.execute(
            f"SELECT enabled, minimum_match_score, apply_mode, confirm_before_submit FROM public.user_application_policies WHERE user_id = {ph}::uuid",
            (current_user.user_id,),
        )
        row = cur.fetchone()
    if not row:
        return {"enabled": False, "min_score": 70, "apply_mode": "automatic", "confirm_before_submit": False}
    d = row if isinstance(row, dict) else dict(row)
    return {
        "enabled": bool(d.get("enabled")),
        "min_score": d.get("minimum_match_score", 70),
        "apply_mode": d.get("apply_mode") or "automatic",
        "confirm_before_submit": bool(d.get("confirm_before_submit")),
    }


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
                INSERT INTO public.user_application_policies (user_id, enabled, minimum_match_score, apply_mode, confirm_before_submit, updated_at)
                VALUES ({ph}::uuid, {ph}, {ph}, {ph}, {ph}, NOW())
                ON CONFLICT (user_id) DO UPDATE
                SET enabled = EXCLUDED.enabled, minimum_match_score = EXCLUDED.minimum_match_score,
                    apply_mode = EXCLUDED.apply_mode, confirm_before_submit = EXCLUDED.confirm_before_submit, updated_at = NOW()
                """,
                (current_user.user_id, body.enabled, body.min_score, body.apply_mode, body.confirm_before_submit),
            )
        else:
            conn.execute(
                f"""
                INSERT OR REPLACE INTO public.user_application_policies (user_id, enabled, minimum_match_score, apply_mode, confirm_before_submit)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
                """,
                (current_user.user_id, body.enabled, body.min_score, body.apply_mode, body.confirm_before_submit),
            )
        conn.commit()
    return {"enabled": body.enabled, "min_score": body.min_score, "apply_mode": body.apply_mode, "confirm_before_submit": body.confirm_before_submit}


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


@router.get("/cover-letters")
def list_generated_cover_letters(current_user: CurrentUser = Depends(get_current_user)):
    """Cover letters the auto-apply pipeline generated for this user's real
    (non-test-mode) submissions -- see
    resume_intelligence/cover_letter/auto_generate.py. Paid-tier only at
    generation time, so an empty list here just as plausibly means "free
    tier" or "no real submissions yet" as it does "feature broken"."""
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        cur = conn.execute(
            f"""
            SELECT id, job_id, company_name, job_title, cover_letter_text, word_count, created_at
            FROM public.generated_cover_letters
            WHERE user_id = {ph}::uuid
            ORDER BY created_at DESC
            LIMIT 100
            """,
            (current_user.user_id,),
        )
        rows = cur.fetchall()

    return {
        "items": [
            {
                "id": str((r if isinstance(r, dict) else dict(r)).get("id")),
                "job_id": str((r if isinstance(r, dict) else dict(r)).get("job_id")),
                "company_name": (r if isinstance(r, dict) else dict(r)).get("company_name") or "",
                "job_title": (r if isinstance(r, dict) else dict(r)).get("job_title") or "",
                "cover_letter_text": (r if isinstance(r, dict) else dict(r)).get("cover_letter_text") or "",
                "word_count": (r if isinstance(r, dict) else dict(r)).get("word_count"),
                "created_at": str((r if isinstance(r, dict) else dict(r)).get("created_at")),
            }
            for r in rows
        ]
    }


@router.get("/captcha/active")
def get_active_captcha(current_user: CurrentUser = Depends(get_current_user)):
    """Polled by the dashboard to discover "is a background run of mine
    currently stuck on a CAPTCHA right now" without already knowing a
    session_id."""
    session_id = captcha_bridge.get_active_session_id_for_user(current_user.user_id)
    if not session_id:
        return {"active": False}
    session = captcha_bridge.get_session(session_id)
    return {
        "active": True,
        "session_id": session_id,
        "job_id": session.get("job_id") if session else None,
        "reason": session.get("reason", "captcha") if session else "captcha",
    }


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


class CaptchaType(BaseModel):
    text: str


@router.post("/captcha/{session_id}/type")
def captcha_type(session_id: str, body: CaptchaType, current_user: CurrentUser = Depends(get_current_user)):
    """Types into whatever field currently has focus on the live page --
    the google_connect flow's email/password/2FA entry needs real text
    input, not just clicks."""
    _require_own_session(session_id, current_user)
    ok = captcha_bridge.request_type(session_id, body.text)
    return {"ok": ok}


@router.post("/google/connect")
def start_google_connect(current_user: CurrentUser = Depends(get_current_user)):
    """Launches a live, human-driven Google login (see google_connect.py)
    so future sign-in-gated Google Forms can be submitted using the
    resulting session instead of hitting REVIEW_REQUIRED every time."""
    if captcha_bridge.get_active_session_id_for_user(current_user.user_id):
        raise HTTPException(status_code=409, detail="Another live session is already active for this account.")
    from src.applications.google_connect import start_connect_flow
    start_connect_flow(current_user.user_id)
    return {"ok": True}


@router.get("/google/connect/status")
def google_connect_status(current_user: CurrentUser = Depends(get_current_user)):
    from src.applications import google_session
    return {"connected": google_session.has_session(current_user.user_id)}


@router.post("/google/connect/disconnect")
def disconnect_google(current_user: CurrentUser = Depends(get_current_user)):
    from src.applications import google_session
    google_session.delete_session(current_user.user_id)
    return {"ok": True}
