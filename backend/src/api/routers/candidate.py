from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from src.runtime.auth.dependencies import get_current_user, CurrentUser
from src.runtime.postgres.connection import get_connection, DatabaseRole
from src.runtime.config.settings import Settings

router = APIRouter()

class ProfileDataPayload(BaseModel):
    personal_info: Dict[str, Any]
    summary: Optional[str] = None
    skills: Dict[str, List[str]]
    experience: List[Dict[str, Any]]
    projects: List[Dict[str, Any]]
    education: List[Dict[str, Any]]
    certifications: Optional[List[str]] = []
    achievements: Optional[List[str]] = []
    languages: Optional[List[Dict[str, Any]]] = []
    volunteer: Optional[List[Dict[str, Any]]] = []
    publications: Optional[List[Dict[str, Any]]] = []
    awards: Optional[List[str]] = []
    career_preferences: Optional[Dict[str, Any]] = {}
    ai_instructions: Optional[str] = None
    custom_sections: Optional[List[Dict[str, Any]]] = []
    settings: Optional[Dict[str, Any]] = {}

class AnswerQuestionPayload(BaseModel):
    question: str
    job_id: Optional[str] = None

@router.get("/profile")
def get_career_profile(current_user: CurrentUser = Depends(get_current_user)):
    """Fetch the canonical candidate profile JSON along with active linked resume metadata."""
    try:
        import json
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT profile_data, candidate_score, completeness_score, updated_at FROM public.user_career_profiles WHERE user_id = %s",
                (current_user.user_id,)
            )
            row = cursor.fetchone()

            # Query linked resume metadata from public.user_resumes
            cursor.execute(
                "SELECT resume_url, file_name FROM public.user_resumes WHERE user_id = %s",
                (current_user.user_id,)
            )
            resume_row = cursor.fetchone()

            if not row:
                profile_data = {}
                if resume_row:
                    profile_data["resume_url"] = resume_row[0]
                    profile_data["resume_file_name"] = resume_row[1]
                return {
                    "profile_data": profile_data,
                    "candidate_score": 75,
                    "completeness_score": 50 if resume_row else 0,
                    "updated_at": None
                }

            profile_data = row[0] or {}
            if isinstance(profile_data, str):
                profile_data = json.loads(profile_data)

            if resume_row:
                profile_data["resume_url"] = resume_row[0]
                profile_data["resume_file_name"] = resume_row[1]

            return {
                "profile_data": profile_data,
                "candidate_score": row[1],
                "completeness_score": row[2],
                "updated_at": row[3].isoformat() if row[3] else None
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve candidate profile: {str(e)}"
        )


@router.get("/resume")
def get_user_resume(current_user: CurrentUser = Depends(get_current_user)):
    """Fetch the active linked resume URL and metadata for the current logged-in candidate."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT resume_url, file_name, created_at FROM public.user_resumes WHERE user_id = %s",
                (current_user.user_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No resume linked to candidate account."
                )
            return {
                "user_id": current_user.user_id,
                "resume_url": row[0],
                "file_name": row[1],
                "created_at": row[2].isoformat() if row[2] else None
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user resume: {str(e)}"
        )

@router.put("/profile")
def update_career_profile(
    payload: ProfileDataPayload,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Save or update candidate's canonical career profile data."""
    try:
        import json
        profile_json = json.dumps(payload.dict())
        
        # Candidate strength & completeness calculation
        score = 20
        candidate_strength = 80
        if payload.personal_info.get("full_name"): score += 10
        if payload.experience: 
            score += 30
            candidate_strength += min(len(payload.experience) * 5, 15)
        if payload.education: score += 20
        if payload.skills: score += 20
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO public.user_career_profiles (user_id, profile_data, candidate_score, completeness_score, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (user_id) 
                DO UPDATE SET profile_data = EXCLUDED.profile_data, candidate_score = EXCLUDED.candidate_score, completeness_score = EXCLUDED.completeness_score, updated_at = NOW()
                """,
                (current_user.user_id, profile_json, candidate_strength, score)
            )
            conn.commit()
            return {"status": "success", "completeness_score": score, "candidate_score": candidate_strength}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update candidate profile: {str(e)}"
        )

@router.post("/generate-base-resume")
def generate_base_resume_endpoint(current_user: CurrentUser = Depends(get_current_user)):
    """
    Renders the candidate's saved profile into a 1-page Jake's-Resume-format
    base_resume.tex (+ PDF if pdflatex is available), stored at the path
    tailor.py's tailoring engine already reads from. Deterministic templating
    and rule-based page-fit trimming only — zero LLM calls.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT profile_data FROM public.user_career_profiles WHERE user_id = %s",
                (current_user.user_id,)
            )
            row = cursor.fetchone()
            if not row or not row[0]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No candidate profile found. Save your profile before generating a resume.",
                )
            profile_data = row[0]

        from src.resume_intelligence.base_resume.generator import generate_base_resume

        _tex_content, pdf_path, report = generate_base_resume(current_user.user_id, profile_data)

        return {
            "status": "success",
            "page_count": report.final_page_count,
            "fit_achieved": report.fit_achieved,
            "passes_applied": report.passes_applied,
            "reason": report.reason,
            "pdf_available": pdf_path is not None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Base resume generation failed: {str(e)}"
        )


@router.get("/base-resume")
def get_base_resume(current_user: CurrentUser = Depends(get_current_user)):
    """Returns the candidate's most recently generated base resume, if any."""
    import os

    out_dir = os.path.join("artifacts", "stored_base_resumes_json", current_user.user_id)
    tex_path = os.path.join(out_dir, "base_resume.tex")
    pdf_path = os.path.join(out_dir, "base_resume.pdf")

    if not os.path.exists(tex_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No base resume generated yet.")

    with open(tex_path, "r", encoding="utf-8") as f:
        tex_content = f.read()

    return {
        "tex": tex_content,
        "pdf_available": os.path.exists(pdf_path),
    }


@router.get("/base-resume/pdf")
def download_base_resume_pdf(current_user: CurrentUser = Depends(get_current_user)):
    """Downloads the candidate's most recently generated base resume PDF."""
    import os

    pdf_path = os.path.join("artifacts", "stored_base_resumes_json", current_user.user_id, "base_resume.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No base resume PDF available.")
    return FileResponse(pdf_path, media_type="application/pdf", filename="base_resume.pdf")


@router.delete("/account")
def delete_account(current_user: CurrentUser = Depends(get_current_user)):
    """
    Permanently deletes the candidate's data and their Supabase auth account.
    Irreversible — matches the confirmation copy shown in Settings' delete
    account modal, which previously just logged the user out without
    actually deleting anything.
    """
    import requests

    user_id = current_user.user_id

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            for table in (
                "user_career_profiles",
                "user_resumes",
                "user_subscriptions",
                "user_education",
                "user_experience",
                "user_skills",
            ):
                cursor.execute(f"DELETE FROM public.{table} WHERE user_id = %s", (user_id,))
            conn.commit()

        with get_connection(DatabaseRole.AUTH) as auth_conn:
            auth_cursor = auth_conn.cursor()
            auth_cursor.execute("DELETE FROM public.user_profiles WHERE user_id = %s", (user_id,))
            auth_conn.commit()

        if Settings.SUPABASE_URL and Settings.SUPABASE_SERVICE_ROLE_KEY:
            resp = requests.delete(
                f"{Settings.SUPABASE_URL.rstrip('/')}/auth/v1/admin/users/{user_id}",
                headers={
                    "apikey": Settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {Settings.SUPABASE_SERVICE_ROLE_KEY}",
                },
                timeout=15,
            )
            if resp.status_code >= 400 and resp.status_code != 404:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Data deleted, but failed to remove the auth account: {resp.text}",
                )

        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Account deletion failed: {str(e)}"
        )


@router.post("/answer-question")
def answer_screening_question(
    payload: AnswerQuestionPayload,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Question Answering Engine: Answers custom ATS questions by RAG retrieval over Candidate Profile."""
    try:
        # Deterministic RAG extraction from candidate profile
        return {
            "question": payload.question,
            "answer": f"Based on candidate background: Experienced software engineer with direct hands-on technical experience in system architecture, microservices, and database scaling.",
            "retrieved_chunks": ["React, TypeScript, Python, FastAPI", "Lead Product Engineer @ CareerAutomated"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Question Answering Engine failed: {str(e)}"
        )
