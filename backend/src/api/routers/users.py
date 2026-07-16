from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from src.runtime.auth.dependencies import get_current_user, CurrentUser
from src.runtime.postgres.connection import get_connection

router = APIRouter()

class EducationItem(BaseModel):
    institution: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None

class ExperienceItem(BaseModel):
    company: str
    title: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None

class SkillItem(BaseModel):
    skill_name: str
    proficiency: Optional[str] = None

class OnboardingPayload(BaseModel):
    full_name: str
    career_goals: str
    education: List[EducationItem]
    experience: List[ExperienceItem]
    skills: List[SkillItem]
    resume_url: Optional[str] = None
    resume_file_name: Optional[str] = None


@router.get("/me", response_model=CurrentUser)
def get_me(current_user: CurrentUser = Depends(get_current_user)):
    """Fetch profile of current authenticated user."""
    return current_user


@router.put("/onboarding")
def complete_onboarding(
    payload: OnboardingPayload,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Save onboarding profile items and mark onboarding_complete = true."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Update public.user_profiles with full_name, career_goals, onboarding_complete = true
            cursor.execute(
                """
                UPDATE public.user_profiles 
                SET full_name = %s, career_goals = %s, onboarding_complete = TRUE, updated_at = NOW()
                WHERE user_id = %s
                """,
                (payload.full_name, payload.career_goals, current_user.user_id)
            )
            
            # Clean up old records for this user to ensure idempotency
            cursor.execute("DELETE FROM public.user_education WHERE user_id = %s", (current_user.user_id,))
            cursor.execute("DELETE FROM public.user_experience WHERE user_id = %s", (current_user.user_id,))
            cursor.execute("DELETE FROM public.user_skills WHERE user_id = %s", (current_user.user_id,))
            
            # 2. Insert Education
            for edu in payload.education:
                cursor.execute(
                    """
                    INSERT INTO public.user_education (user_id, institution, degree, field_of_study, start_year, end_year)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (current_user.user_id, edu.institution, edu.degree, edu.field_of_study, edu.start_year, edu.end_year)
                )
                
            # 3. Insert Experience
            for exp in payload.experience:
                cursor.execute(
                    """
                    INSERT INTO public.user_experience (user_id, company, title, start_date, end_date, description)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (current_user.user_id, exp.company, exp.title, exp.start_date, exp.end_date, exp.description)
                )
                
            # 4. Insert Skills
            for skill in payload.skills:
                cursor.execute(
                    """
                    INSERT INTO public.user_skills (user_id, skill_name, proficiency)
                    VALUES (%s, %s, %s)
                    """,
                    (current_user.user_id, skill.skill_name, skill.proficiency)
                )
                
            # 5. Insert Resume metadata if provided
            if payload.resume_url and payload.resume_file_name:
                cursor.execute("DELETE FROM public.user_resumes WHERE user_id = %s", (current_user.user_id,))
                cursor.execute(
                    """
                    INSERT INTO public.user_resumes (user_id, resume_url, file_name)
                    VALUES (%s, %s, %s)
                    """,
                    (current_user.user_id, payload.resume_url, payload.resume_file_name)
                )
                
            conn.commit()
            return {"status": "success", "message": "Onboarding profile saved successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save onboarding details: {str(e)}"
        )


import os
import shutil
import tempfile
from fastapi import UploadFile, File
from src.runtime.storage.storage_service import StorageService

@router.post("/upload_resume")
def upload_resume(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Upload resume file to Cloudflare R2 and return the storage key/url."""
    # Enforce PDF and DOCX formats only
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".docx"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and DOCX formats are supported for resume uploads"
        )
        
    # Save UploadFile stream to a temporary file locally
    suffix = ext
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        try:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to write file stream: {str(e)}"
            )
            
    # Upload to Cloudflare R2
    key = f"resumes/{current_user.user_id}/{file.filename}"
    try:
        success = StorageService.upload_file(tmp_path, key)
        if not success:
            raise Exception("R2 adapter rejected upload")
            
        # Get signed or public download url
        download_url = StorageService.generate_signed_download_url(key, expires_in=604800) # 7 days
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload resume to Cloudflare R2: {str(e)}"
        )
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            
    return {
        "status": "success",
        "key": key,
        "url": download_url,
        "file_name": file.filename
    }
