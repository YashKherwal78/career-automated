from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from src.runtime.auth.dependencies import get_current_user, CurrentUser
from src.runtime.postgres.connection import get_connection, DatabaseRole

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
    career_goals: Optional[str] = None
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
        # user_profiles (incl. onboarding_complete, read by get_current_user) lives in the
        # Supabase auth database, not the operational one — see dependencies.py's note.
        # It has no career_goals column; that's collected elsewhere (Dashboard modal).
        with get_connection(DatabaseRole.AUTH) as auth_conn:
            auth_cursor = auth_conn.cursor()
            auth_cursor.execute(
                """
                UPDATE public.user_profiles
                SET full_name = %s, onboarding_complete = TRUE, updated_at = NOW()
                WHERE user_id = %s
                """,
                (payload.full_name, current_user.user_id)
            )
            auth_conn.commit()

        with get_connection() as conn:
            cursor = conn.cursor()

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

            # 6. Upsert canonical profile into user_career_profiles
            skills_dict = {}
            for s in payload.skills:
                skills_dict.setdefault("general", []).append(s.skill_name)

            exp_list = [
                {
                    "company": e.company,
                    "role": e.title,
                    "start_date": e.start_date or "",
                    "end_date": e.end_date or "",
                    "description": e.description or "",
                }
                for e in payload.experience
            ]

            edu_list = [
                {
                    "institution": e.institution,
                    "degree": e.degree or "",
                    "field_of_study": e.field_of_study or "",
                }
                for e in payload.education
            ]

            profile_data_obj = {
                "personal_info": {
                    "full_name": payload.full_name,
                    "email": current_user.email,
                },
                "skills": skills_dict,
                "experience": exp_list,
                "education": edu_list,
                "projects": [],
                "certifications": [],
                "resume_url": payload.resume_url or "",
                "resume_file_name": payload.resume_file_name or "",
            }

            import json
            profile_json = json.dumps(profile_data_obj)
            completeness = 20
            if exp_list: completeness += 30
            if edu_list: completeness += 20
            if skills_dict: completeness += 30

            cursor.execute(
                """
                INSERT INTO public.user_career_profiles (user_id, profile_data, candidate_score, completeness_score, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (user_id) 
                DO UPDATE SET profile_data = EXCLUDED.profile_data, candidate_score = EXCLUDED.candidate_score, completeness_score = EXCLUDED.completeness_score, updated_at = NOW()
                """,
                (current_user.user_id, profile_json, 85, completeness)
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
from src.services.profile_extractor import ProfileExtractionService

@router.post("/extract_profile")
def extract_profile_endpoint(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Upload resume or document, extract text, and extract a canonical candidate profile."""
    ext = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = {".pdf", ".docx", ".txt"}
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only PDF, DOCX, and TXT formats are supported. Got: {ext or 'unknown'}"
        )
        
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

    try:
        # Extract profile using ProfileExtractionService
        extractor = ProfileExtractionService()
        parsed_data = extractor.extract_profile(tmp_path)
        
        # Also upload to Cloudflare R2
        key = f"resumes/{current_user.user_id}/{file.filename}"
        StorageService.upload_file(tmp_path, key)
        download_url = StorageService.generate_signed_download_url(key, expires_in=604800)
        
        parsed_data["resume_url"] = download_url
        parsed_data["resume_file_name"] = file.filename

        # Save resume URL/file metadata to PostgreSQL user_resumes & user_career_profiles
        import json
        profile_json = json.dumps(parsed_data)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM public.user_resumes WHERE user_id = %s", (current_user.user_id,))
            cursor.execute(
                """
                INSERT INTO public.user_resumes (user_id, resume_url, file_name)
                VALUES (%s, %s, %s)
                """,
                (current_user.user_id, download_url, file.filename)
            )
            cursor.execute(
                """
                INSERT INTO public.user_career_profiles (user_id, profile_data, candidate_score, completeness_score, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (user_id) 
                DO UPDATE SET profile_data = EXCLUDED.profile_data, candidate_score = EXCLUDED.candidate_score, completeness_score = EXCLUDED.completeness_score, updated_at = NOW()
                """,
                (current_user.user_id, profile_json, 85, 80)
            )
            conn.commit()

        try:
            from src.discovery.embeddings import embed_candidate_text_with_retry, candidate_embedding_text
            from src.core.repositories.job.repository import JobRepository
            vec = embed_candidate_text_with_retry(candidate_embedding_text(parsed_data))
            JobRepository().store_candidate_embedding(current_user.user_id, vec)
        except Exception as embed_err:
            import logging
            logging.getLogger("users").warning(f"Candidate embedding update failed after retries: {embed_err}")

        # Separate try/except, same reasoning as the v1 block above -- a v2
        # failure must never block the v1 embedding live search depends on.
        try:
            from src.discovery.embeddings import embed_candidate_text_with_retry, candidate_embedding_text
            from src.core.repositories.job.repository import JobRepository
            vec_v2 = embed_candidate_text_with_retry(candidate_embedding_text(parsed_data), v2=True)
            JobRepository().store_candidate_embedding_v2(current_user.user_id, vec_v2)
        except Exception as embed_v2_err:
            import logging
            logging.getLogger("users").warning(f"Candidate embedding_v2 update failed after retries: {embed_v2_err}")

        return parsed_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile extraction failed: {str(e)}"
        )
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/upload_resume")
def upload_resume(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Upload resume file to Cloudflare R2 and return the storage key/url."""
    # Enforce PDF, DOCX, and TXT formats only
    ext = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = {".pdf", ".docx", ".txt"}
    allowed_mime_types = {
        ".pdf":  "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt":  "text/plain",
    }
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only PDF, DOCX, and TXT formats are supported. Got: {ext or 'unknown'}"
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
