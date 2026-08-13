"""
Tailoring Engine V1 — REST API Router.

POST /resume/tailor
  Loads base .tex and StructuredJobProfile, runs TailoringEngineV1, returns result.
  Never writes to DB — tailored resumes are always ephemeral.

POST /resume/tailor/preview
  Same as /tailor but returns only the diff_log and keyword_coverage.
  No .tex in response. Used by the dashboard to show what would change.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from src.api.db import get_db
from src.runtime.auth.dependencies import get_current_user, CurrentUser
from src.resume_intelligence.tailoring.engine_v1 import TailoringEngineV1
from src.resume_intelligence.tailoring.models_v1 import (
    HardBlockError,
    TailoringInput,
    TailoringResult,
)
from src.resume_intelligence.cover_letter.generator import CoverLetterGenerator
from src.resume_intelligence.cover_letter.models import CoverLetterInput

# Cover letter generation is a paid-tier feature — it's an extra LLM call
# on top of the (already-paid-tier-gateable) tailoring flow, so it costs
# real money per use unlike the deterministic, zero-LLM base resume
# generator. The product owner's own account is exempt.
FREE_ACCESS_EMAILS = {"yash.kherwal78@gmail.com"}

logger = logging.getLogger("TailoringRouter")
router = APIRouter(prefix="/resume", tags=["Resume Tailoring"])

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class TailorRequest(BaseModel):
    candidate_id: str
    # Either job_id (tailor against an already-tracked job) or job_description
    # (paste-your-own JD, parsed ad hoc) must be provided — see _resolve_jd_profile.
    job_id: Optional[str] = None
    job_description: Optional[str] = None
    company_name: Optional[str] = None
    role_title: Optional[str] = None
    confidence_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    llm_provider: str = "groq"
    llm_model: str = "llama-3.3-70b-versatile"


class TailorResponse(BaseModel):
    job_id: str
    candidate_id: str
    tailored_tex: str
    is_noop: bool
    keyword_coverage: float
    llm_calls_made: int
    integrity_passed: bool
    policy_passed: bool
    diff_summary: Dict[str, Any] = Field(default_factory=dict)
    version_metadata: Dict[str, str] = Field(default_factory=dict)
    is_persisted: bool = False


class TailoredPdfRequest(BaseModel):
    tailored_tex: str


class CoverLetterRequest(BaseModel):
    candidate_id: str
    job_id: Optional[str] = None
    job_description: Optional[str] = None
    company_name: Optional[str] = None
    role_title: Optional[str] = None


class CoverLetterResponse(BaseModel):
    job_id: str
    candidate_id: str
    cover_letter_text: str
    word_count: int
    llm_calls_made: int


class TailorPreviewResponse(BaseModel):
    job_id: str
    candidate_id: str
    is_noop: bool
    keyword_coverage: float
    diff_log: list = Field(default_factory=list)
    policy_warnings: list = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers: load base .tex and jd_profile from storage
# ---------------------------------------------------------------------------

def _load_base_tex(candidate_id: str, db) -> str:
    """
    Load the stored base .tex for a candidate from the same persisted
    location the base-resume generator writes to (see
    resume_intelligence/base_resume/generator.py -- this used to be a bare
    "artifacts/..." relative path resolved against the container's
    ephemeral filesystem, not the mounted data volume, so a freshly
    generated base resume could 404 here immediately after being "saved").
    """
    import os
    from src.resume_intelligence.base_resume.generator import BASE_RESUME_STORAGE_DIR

    tex_path = os.path.join(BASE_RESUME_STORAGE_DIR, candidate_id, "base_resume.tex")
    if os.path.exists(tex_path):
        with open(tex_path, "r", encoding="utf-8") as f:
            return f.read()

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No base resume found for your account yet. Generate one from the Resume page first.",
    )


def _load_jd_profile(job_id: str, db) -> Dict[str, Any]:
    """
    Build a StructuredJobProfile for job_id from normalized_jobs.

    normalized_jobs has no jd_profile_json column (that structured-parse pipeline
    stage doesn't exist yet), so this parses the job's raw title/description with
    JobDescriptionParser on every call rather than reading a cached column.
    """
    try:
        from src.resume_intelligence.job_intelligence.parser import JobDescriptionParser
        from src.api.db import json_extract

        cursor = db.cursor()
        json_company = json_extract("n.raw_payload_json", "$.company")
        cursor.execute(
            f"""
            SELECT n.title, n.description,
                   COALESCE(i.canonical_name, {json_company}, n.company_id) AS company_name
            FROM normalized_jobs n
            LEFT JOIN company_identities i ON n.company_id = i.company_id
            WHERE n.job_id = %s
            LIMIT 1
            """,
            (job_id,),
        )
        row = cursor.fetchone()
        # Postgres connections use a dict_row factory (columns by name); sqlite falls
        # back to plain tuples. Handle both rather than assuming positional access.
        if row and hasattr(row, "keys"):
            title, description, company_name = row["title"], row["description"], row["company_name"]
        elif row:
            title, description, company_name = row[0], row[1], row[2]
        else:
            title = description = company_name = None
        if description:
            profile = JobDescriptionParser().parse_job_description(
                job_id=job_id,
                company_name=company_name or "Unknown",
                role_title=title or "Software Engineer",
                raw_description=description,
            )
            return profile.model_dump()
    except Exception as exc:
        logger.warning("JD parse failed for job_id=%s: %s", job_id, exc)

    # Graceful fallback: return a minimal profile for development/testing
    logger.warning("Using empty jd_profile fallback for job_id=%s", job_id)
    return {
        "job_id": job_id,
        "company_name": "Unknown",
        "role_title": "Software Engineer",
        "ats_keywords": [],
        "required_skills": [],
        "technologies": [],
        "responsibilities": [],
        "strategy_signals": {
            "role_type": "Software Engineer",
            "primary_domain": "Tech",
            "summary_strategy": "Calibrate narrative towards the role.",
            "bullet_strategy": "Emphasize system design and technical impact.",
            "preferred_ownership_style": "OWNER",
            "priority_keywords": [],
            "priority_project_types": [],
        },
    }


def _resolve_jd_profile(request: "TailorRequest", db) -> tuple[str, Dict[str, Any]]:
    """
    Resolves (effective_job_id, jd_profile) from either an existing tracked
    job_id (DB lookup, never re-parses) or a pasted job_description (parsed
    ad hoc, no DB involved) — the free-text path a candidate uses when the
    job isn't one CareerAutomated has already discovered.
    """
    if request.job_id:
        return request.job_id, _load_jd_profile(request.job_id, db)

    if request.job_description:
        import uuid
        from src.resume_intelligence.job_intelligence.parser import JobDescriptionParser

        adhoc_id = f"adhoc-{uuid.uuid4().hex[:12]}"
        try:
            profile = JobDescriptionParser().parse_job_description(
                job_id=adhoc_id,
                company_name=request.company_name or "Unknown",
                role_title=request.role_title or "Software Engineer",
                raw_description=request.job_description,
            )
            return adhoc_id, profile.model_dump()
        except Exception as exc:
            logger.warning("Ad-hoc JD parse failed: %s", exc)
            return adhoc_id, {
                "job_id": adhoc_id,
                "company_name": request.company_name or "Unknown",
                "role_title": request.role_title or "Software Engineer",
                "ats_keywords": [],
                "required_skills": [],
                "technologies": [],
                "responsibilities": [],
                "strategy_signals": {
                    "role_type": "Software Engineer",
                    "primary_domain": "Tech",
                    "summary_strategy": "Calibrate narrative towards the role.",
                    "bullet_strategy": "Emphasize system design and technical impact.",
                    "preferred_ownership_style": "OWNER",
                    "priority_keywords": [],
                    "priority_project_types": [],
                },
            }

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Provide either job_id or job_description.",
    )


def _load_candidate_memory(candidate_id: str, db) -> Dict[str, Any]:
    """
    Derive candidate memory ("global" facts for summary building, per
    CandidateMemory's schema) from the real candidate profile.

    There is no dedicated candidate-memory store — nothing in this codebase
    ever writes one — so this reads the actual populated profile data
    (public.user_career_profiles, written by candidate.py) and distills it
    into short facts instead of querying a table nothing ever fills.
    """
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT profile_data FROM public.user_career_profiles WHERE user_id = %s LIMIT 1",
            (candidate_id,)
        )
        row = cursor.fetchone()
        profile_data = row["profile_data"] if row else None
        if not profile_data:
            return {}
        profile = profile_data
        if isinstance(profile, str):
            import json
            profile = json.loads(profile)

        facts: list[str] = []
        experience = profile.get("experience") or []
        if experience:
            facts.append(f"{len(experience)} professional role(s) on record.")
            latest = experience[0]
            role = latest.get("role") or latest.get("title")
            company = latest.get("company")
            if role and company:
                facts.append(f"Most recent role: {role} at {company}.")

        skills = profile.get("skills") or {}
        all_skills = [s for group in skills.values() if isinstance(group, list) for s in group]
        if all_skills:
            facts.append(f"Core skills: {', '.join(all_skills[:10])}.")

        education = profile.get("education") or []
        if education:
            top = education[0]
            degree = top.get("degree")
            institution = top.get("institution")
            if degree and institution:
                facts.append(f"Education: {degree}, {institution}.")

        return {"global": facts} if facts else {}
    except Exception:
        logger.warning("Candidate memory derivation failed for candidate_id=%s", candidate_id, exc_info=True)
        return {}


def _load_ai_preferences(candidate_id: str, db) -> tuple[str, str]:
    """
    Reads the candidate's saved Settings > AI Preferences (writing tone,
    tailoring aggressiveness) from the same profile_data blob Settings
    persists to (see useSettingsPersistence in settings.tsx — these were
    previously saved but never read anywhere, including here).
    """
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT profile_data FROM public.user_career_profiles WHERE user_id = %s LIMIT 1",
            (candidate_id,)
        )
        row = cursor.fetchone()
        profile_data = row["profile_data"] if row else None
        if not profile_data:
            return "Professional", "Balanced"
        profile = profile_data
        if isinstance(profile, str):
            import json
            profile = json.loads(profile)
        ai_settings = (profile.get("settings") or {}).get("ai") or {}
        return (
            ai_settings.get("writingTone") or "Professional",
            ai_settings.get("tailoringAggro") or "Balanced",
        )
    except Exception:
        logger.warning("AI preference lookup failed for candidate_id=%s", candidate_id, exc_info=True)
        return "Professional", "Balanced"


def _has_cover_letter_access(current_user: "CurrentUser", db) -> bool:
    """Pro-tier gate. Delegates to src.billing.access.has_paid_access --
    the same check now also used by the auto-apply pipeline to decide
    whether to generate a cover letter for a real submission, so this and
    that stay in sync instead of drifting as two copies of the same query."""
    from src.billing.access import has_paid_access
    return has_paid_access(current_user.user_id, current_user.email)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/tailor", response_model=TailorResponse, status_code=status.HTTP_200_OK)
def tailor_resume(request: TailorRequest, db=Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    """
    Tailor the candidate's base resume for a specific job.

    Loads the pre-parsed StructuredJobProfile from normalized_jobs (never re-parses JD).
    Runs TailoringEngineV1 and returns the ephemeral tailored .tex.
    Result is never written to DB.
    """
    # This router is mounted with a router-level auth dependency, so every
    # caller here is a *logged-in* user -- but candidate_id came from the
    # request body, not the session, so without this check any logged-in
    # user could pass someone else's candidate_id and get their base resume
    # text, career-profile facts, and AI tone preferences back (an IDOR:
    # authenticated, but not authorized for the specific resource).
    if request.candidate_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="candidate_id does not match the authenticated user")
    logger.info("POST /resume/tailor — candidate=%s, job=%s", request.candidate_id, request.job_id or "(pasted JD)")

    base_tex = _load_base_tex(request.candidate_id, db)
    effective_job_id, jd_profile = _resolve_jd_profile(request, db)
    candidate_memory = _load_candidate_memory(request.candidate_id, db)
    writing_tone, tailoring_aggressiveness = _load_ai_preferences(request.candidate_id, db)

    engine = TailoringEngineV1()
    inp = TailoringInput(
        base_tex=base_tex,
        candidate_memory=candidate_memory,
        jd_profile=jd_profile,
        confidence_threshold=request.confidence_threshold,
        llm_provider=request.llm_provider,
        llm_model=request.llm_model,
        job_id=effective_job_id,
        writing_tone=writing_tone,
        tailoring_aggressiveness=tailoring_aggressiveness,
    )

    try:
        result: TailoringResult = engine.tailor(inp)
    except HardBlockError as exc:
        logger.error("HardBlockError for job=%s: %s", effective_job_id, exc.violations)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Tailoring integrity check failed",
                "violations": exc.violations,
            },
        )
    except Exception as exc:
        logger.exception("Unexpected tailoring error for job=%s", effective_job_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tailoring engine error: {str(exc)}",
        )

    return TailorResponse(
        job_id=result.job_id,
        candidate_id=request.candidate_id,
        tailored_tex=result.tailored_tex,
        is_noop=result.is_noop,
        keyword_coverage=result.keyword_coverage,
        llm_calls_made=result.llm_calls_made,
        integrity_passed=result.integrity_report.passed,
        policy_passed=result.policy_report.passed,
        diff_summary={
            "total_bullets": len(result.diff_log),
            "bullets_changed": sum(1 for d in result.diff_log if not d.kept_original),
            "keywords_added": list({kw for d in result.diff_log for kw in d.keywords_added}),
            "xyz_compliance": result.policy_report.xyz_compliance,
        },
        version_metadata={
            "prompt_version": result.version_metadata.prompt_version,
            "rules_version": result.version_metadata.rules_version,
            "knowledge_version": result.version_metadata.knowledge_version,
            "llm_model": result.version_metadata.llm_model,
        },
        is_persisted=False,
    )


@router.post("/tailor/pdf", status_code=status.HTTP_200_OK)
def compile_tailored_pdf(
    request: TailoredPdfRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Compiles a tailored .tex (as returned by POST /tailor) into a PDF and
    streams it back. Nothing is written to permanent storage — same
    ephemeral-by-design compile-on-demand as the rest of tailoring, just
    reusing the base resume generator's pdflatex step so candidates get a
    PDF instead of a raw .tex file they'd need their own LaTeX toolchain
    to open.
    """
    import shutil
    import tempfile

    from src.resume_intelligence.base_resume.renderer import compile_pdf

    tmp_dir = tempfile.mkdtemp(prefix="tailored_resume_")
    try:
        pdf_path = compile_pdf(request.tailored_tex, tmp_dir, filename_prefix="tailored_resume")
        if pdf_path is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="PDF compilation failed for the tailored resume.",
            )
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=tailored_resume.pdf"},
    )


@router.post("/tailor/preview", response_model=TailorPreviewResponse, status_code=status.HTTP_200_OK)
def preview_tailor(request: TailorRequest, db=Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    """
    Preview what the tailoring engine would change — without returning the full .tex.
    Used by the dashboard diff view.
    """
    # Same authorization gap as /tailor above -- see comment there.
    if request.candidate_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="candidate_id does not match the authenticated user")
    logger.info("POST /resume/tailor/preview — candidate=%s, job=%s", request.candidate_id, request.job_id or "(pasted JD)")

    base_tex = _load_base_tex(request.candidate_id, db)
    effective_job_id, jd_profile = _resolve_jd_profile(request, db)
    candidate_memory = _load_candidate_memory(request.candidate_id, db)
    writing_tone, tailoring_aggressiveness = _load_ai_preferences(request.candidate_id, db)

    engine = TailoringEngineV1()
    inp = TailoringInput(
        base_tex=base_tex,
        candidate_memory=candidate_memory,
        jd_profile=jd_profile,
        confidence_threshold=request.confidence_threshold,
        llm_provider=request.llm_provider,
        llm_model=request.llm_model,
        job_id=effective_job_id,
        writing_tone=writing_tone,
        tailoring_aggressiveness=tailoring_aggressiveness,
    )

    try:
        result: TailoringResult = engine.tailor(inp)
    except HardBlockError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "Integrity check failed", "violations": exc.violations},
        )

    return TailorPreviewResponse(
        job_id=result.job_id,
        candidate_id=request.candidate_id,
        is_noop=result.is_noop,
        keyword_coverage=result.keyword_coverage,
        diff_log=[d.model_dump() for d in result.diff_log],
        policy_warnings=result.policy_report.warnings,
    )


@router.post("/cover-letter", response_model=CoverLetterResponse, status_code=status.HTTP_200_OK)
def generate_cover_letter(
    request: CoverLetterRequest,
    db=Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Generate a short, tailored, Problem-Solution-format cover letter for a
    specific job. Pro-tier feature — costs a real LLM call per use, unlike
    the deterministic zero-LLM base resume generator.
    """
    if not _has_cover_letter_access(current_user, db):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Cover letter generation is a Pro feature. Upgrade to generate one.",
        )
    # Same authorization gap as /tailor -- being a paying user isn't the
    # same as being authorized for the specific candidate_id in the body.
    if request.candidate_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="candidate_id does not match the authenticated user")

    logger.info("POST /resume/cover-letter — candidate=%s, job=%s", request.candidate_id, request.job_id or "(pasted JD)")

    # Reuse the exact same JD-resolution and candidate-facts helpers /tailor
    # already relies on — no separate JD parse, no separate profile query.
    tailor_request = TailorRequest(
        candidate_id=request.candidate_id,
        job_id=request.job_id,
        job_description=request.job_description,
        company_name=request.company_name,
        role_title=request.role_title,
    )
    effective_job_id, jd_profile = _resolve_jd_profile(tailor_request, db)
    candidate_memory = _load_candidate_memory(request.candidate_id, db)
    writing_tone, _ = _load_ai_preferences(request.candidate_id, db)
    resume_facts = candidate_memory.get("global", [])

    company_name = request.company_name or jd_profile.get("company_name") or "the company"
    role_title = request.role_title or jd_profile.get("role_title") or "the role"

    generator = CoverLetterGenerator()
    inp = CoverLetterInput(
        candidate_name=current_user.email.split("@")[0],
        candidate_email=current_user.email,
        jd_profile=jd_profile,
        resume_facts=resume_facts,
        company_name=company_name,
        role_title=role_title,
        writing_tone=writing_tone,
    )
    result = generator.generate(inp)

    if result.is_fallback:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cover letter generation failed — either no resume facts are on file yet (save your profile first) or the LLM call failed. Nothing was charged.",
        )

    return CoverLetterResponse(
        job_id=effective_job_id,
        candidate_id=request.candidate_id,
        cover_letter_text=result.cover_letter_text,
        word_count=result.word_count,
        llm_calls_made=result.llm_calls_made,
    )
