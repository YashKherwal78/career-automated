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
from pydantic import BaseModel, Field

from src.api.db import get_db
from src.resume_intelligence.tailoring.engine_v1 import TailoringEngineV1
from src.resume_intelligence.tailoring.models_v1 import (
    HardBlockError,
    TailoringInput,
    TailoringResult,
)

logger = logging.getLogger("TailoringRouter")
router = APIRouter(prefix="/resume", tags=["Resume Tailoring"])

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class TailorRequest(BaseModel):
    candidate_id: str
    job_id: str
    confidence_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    llm_provider: str = "groq"
    llm_model: str = "llama3-70b-8192"


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
    Load the stored base .tex for a candidate.
    Tries artifacts/stored_base_resumes_json/<candidate_id>/base_resume.tex first,
    then falls back to the canonical yash_resume_base_v2.tex for development.
    """
    import os
    tex_path = os.path.join(
        "artifacts", "stored_base_resumes_json", candidate_id, "base_resume.tex"
    )
    if os.path.exists(tex_path):
        with open(tex_path, "r", encoding="utf-8") as f:
            return f.read()

    # Development fallback: use the known base resume
    fallback = "yash_resume_base_v2.tex"
    if os.path.exists(fallback):
        with open(fallback, "r", encoding="utf-8") as f:
            return f.read()

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Base resume .tex not found for candidate_id='{candidate_id}'",
    )


def _load_jd_profile(job_id: str, db) -> Dict[str, Any]:
    """
    Load pre-parsed StructuredJobProfile from normalized_jobs.
    Never re-parses the raw JD — only reads the stored jd_profile_json column.
    """
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT jd_profile_json FROM normalized_jobs WHERE job_id = %s LIMIT 1",
            (job_id,)
        )
        row = cursor.fetchone()
        if row and row[0]:
            import json
            return json.loads(row[0]) if isinstance(row[0], str) else row[0]
    except Exception as exc:
        logger.warning("DB jd_profile load failed for job_id=%s: %s", job_id, exc)

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


def _load_candidate_memory(candidate_id: str, db) -> Dict[str, Any]:
    """Load candidate memory from DB if available. Returns empty dict if not found."""
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT memory_json FROM candidate_profiles WHERE candidate_id = %s LIMIT 1",
            (candidate_id,)
        )
        row = cursor.fetchone()
        if row and row[0]:
            import json
            return json.loads(row[0]) if isinstance(row[0], str) else row[0]
    except Exception:
        pass
    return {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/tailor", response_model=TailorResponse, status_code=status.HTTP_200_OK)
def tailor_resume(request: TailorRequest, db=Depends(get_db)):
    """
    Tailor the candidate's base resume for a specific job.

    Loads the pre-parsed StructuredJobProfile from normalized_jobs (never re-parses JD).
    Runs TailoringEngineV1 and returns the ephemeral tailored .tex.
    Result is never written to DB.
    """
    logger.info("POST /resume/tailor — candidate=%s, job=%s", request.candidate_id, request.job_id)

    base_tex = _load_base_tex(request.candidate_id, db)
    jd_profile = _load_jd_profile(request.job_id, db)
    candidate_memory = _load_candidate_memory(request.candidate_id, db)

    engine = TailoringEngineV1()
    inp = TailoringInput(
        base_tex=base_tex,
        candidate_memory=candidate_memory,
        jd_profile=jd_profile,
        confidence_threshold=request.confidence_threshold,
        llm_provider=request.llm_provider,
        llm_model=request.llm_model,
        job_id=request.job_id,
    )

    try:
        result: TailoringResult = engine.tailor(inp)
    except HardBlockError as exc:
        logger.error("HardBlockError for job=%s: %s", request.job_id, exc.violations)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Tailoring integrity check failed",
                "violations": exc.violations,
            },
        )
    except Exception as exc:
        logger.exception("Unexpected tailoring error for job=%s", request.job_id)
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


@router.post("/tailor/preview", response_model=TailorPreviewResponse, status_code=status.HTTP_200_OK)
def preview_tailor(request: TailorRequest, db=Depends(get_db)):
    """
    Preview what the tailoring engine would change — without returning the full .tex.
    Used by the dashboard diff view.
    """
    logger.info("POST /resume/tailor/preview — candidate=%s, job=%s", request.candidate_id, request.job_id)

    base_tex = _load_base_tex(request.candidate_id, db)
    jd_profile = _load_jd_profile(request.job_id, db)
    candidate_memory = _load_candidate_memory(request.candidate_id, db)

    engine = TailoringEngineV1()
    inp = TailoringInput(
        base_tex=base_tex,
        candidate_memory=candidate_memory,
        jd_profile=jd_profile,
        confidence_threshold=request.confidence_threshold,
        llm_provider=request.llm_provider,
        llm_model=request.llm_model,
        job_id=request.job_id,
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
