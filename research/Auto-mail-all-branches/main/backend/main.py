from __future__ import annotations
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
import tempfile
import subprocess
import shutil
import requests as http_requests

from utils.scraper import parse_job_url, research_company, enrich_recruiter_email
from utils.llm import generate_reply, generate_linkedin_dm, tailor_resume, tailor_latex_resume
from utils.email_sender import send_email
from utils.db import get_profile, upsert_profile

# Load .env
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="Junie AI API", version="2.0.0")

# Allow Vercel frontend and local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://localhost:5174", "http://localhost:5175",
        "http://localhost:8002",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "junie-ai-api", "version": "2.0.0"}


# ── Google OAuth 2.0 ──────────────────────────────────────────────────

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

class AuthCodeRequest(BaseModel):
    code: str
    redirect_uri: str

class RefreshRequest(BaseModel):
    refresh_token: str


@app.post("/api/auth/google")
async def google_auth(req: AuthCodeRequest):
    """Exchange authorization code for tokens + user profile."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured on server. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env")

    # Exchange code for tokens
    token_res = http_requests.post("https://oauth2.googleapis.com/token", data={
        "code": req.code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": req.redirect_uri,
        "grant_type": "authorization_code",
    })

    if token_res.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {token_res.text}")

    tokens = token_res.json()
    access_token = tokens["access_token"]

    # Get user profile
    profile_res = http_requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if profile_res.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch user profile")

    profile = profile_res.json()

    return {
        "email": profile.get("email", ""),
        "name": profile.get("name", ""),
        "picture": profile.get("picture", ""),
        "access_token": access_token,
        "refresh_token": tokens.get("refresh_token", ""),
        "expires_in": tokens.get("expires_in", 3600),
    }


@app.post("/api/auth/refresh")
async def refresh_token(req: RefreshRequest):
    """Refresh an expired access token."""
    token_res = http_requests.post("https://oauth2.googleapis.com/token", data={
        "refresh_token": req.refresh_token,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "grant_type": "refresh_token",
    })

    if token_res.status_code != 200:
        raise HTTPException(status_code=400, detail="Token refresh failed")

    data = token_res.json()
    return {
        "access_token": data["access_token"],
        "expires_in": data.get("expires_in", 3600),
    }


# ── Profile ────────────────────────────────────────────────────────────

class ProfileUpdateRequest(BaseModel):
    email: str
    name: str = ""
    linkedin_url: str = ""
    groq_api_1: str = ""
    hunter_api_key: str = ""
    getprospect_api_key: str = ""
    apollo_api_key: str = ""
    snov_api_key: str = ""
    resume_text: str = ""
    latex_source: str = ""
    resume_bucket_uri: str = ""

@app.get("/api/profile")
async def fetch_user_profile(email: str):
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    profile = get_profile(email)
    return {"profile": profile}

@app.post("/api/profile")
async def update_user_profile(req: ProfileUpdateRequest):
    if not req.email:
        raise HTTPException(status_code=400, detail="Email required")
    updated = upsert_profile(req.model_dump())
    return {"profile": updated}

# ── Models ─────────────────────────────────────────────────────────────

class PipelineRequest(BaseModel):
    job_url: Optional[str] = ""
    additional_context: Optional[str] = ""
    hunter_key: Optional[str] = ""
    getprospect_key: Optional[str] = ""
    apollo_key: Optional[str] = ""
    snov_key: Optional[str] = ""
    groq_key: Optional[str] = ""
    fireworks_key: Optional[str] = ""


class TailorResumeRequest(BaseModel):
    resume_text: str
    job_description: str
    company_name: Optional[str] = ""
    groq_key: Optional[str] = ""
    fireworks_key: Optional[str] = ""

class TailorLatexRequest(BaseModel):
    latex_source: str
    job_description: str
    company_name: Optional[str] = ""
    company_research: Optional[str] = ""
    groq_key: Optional[str] = ""
    fireworks_key: Optional[str] = ""

class GenerateEmailRequest(BaseModel):
    resume_text: str
    job_description: str
    company_name: str
    company_research: str
    recruiter_name: Optional[str] = ""
    additional_context: Optional[str] = ""
    user_name: str
    user_email: str = ""
    linkedin_url: str
    institution: str
    job_url: Optional[str] = ""
    groq_key: Optional[str] = ""
    fireworks_key: Optional[str] = ""


# ── PDF Parse ──────────────────────────────────────────────────────────

import uuid
from utils.pdf_reader import extract_text_from_pdf
from utils.db import supabase

@app.post("/api/parse-pdf")
async def parse_pdf(file: UploadFile = File(...)):
    try:
        content = await file.read()
        text = extract_text_from_pdf(content)
        
        # Push true binary to Supabase Object Storage
        file_id = str(uuid.uuid4())
        bucket_path = f"resume_{file_id}.pdf"
        if supabase:
            supabase.storage.from_("resumes").upload(
                path=bucket_path,
                file=content,
                file_options={"content-type": "application/pdf"}
            )
            return {"text": text, "resume_bucket_uri": bucket_path}
        
        return {"text": text, "resume_bucket_uri": ""}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


# ── Pipeline ───────────────────────────────────────────────────────────

@app.post("/api/pipeline")
async def run_pipeline(req: PipelineRequest):
    """Parses URL, researches company, and finds contacts."""
    effective_hunter = (req.hunter_key or os.getenv("HUNTER_API_KEY", "")).strip()
    if not effective_hunter:
        raise HTTPException(
            status_code=400,
            detail="Hunter.io API key is required for Junie's contact discovery. Add it in profile settings or set HUNTER_API_KEY on the server.",
        )

    job_data = {}
    if req.job_url:
        job_data = parse_job_url(
             req.job_url.strip(),
             api_keys={
                 "groq_key": req.groq_key,
                 "fireworks_key": req.fireworks_key
             }
        )
        if not job_data:
            raise HTTPException(status_code=400, detail="Failed to parse job URL")

    company_name = job_data.get("company_name", "")
    research_data = ""
    if company_name:
        research_data = research_company(company_name)

    progress_log: list = []
    best_email, source, all_contacts = enrich_recruiter_email(
        job_data=job_data,
        additional_context=req.additional_context,
        hunter_api_key=req.hunter_key or os.getenv("HUNTER_API_KEY", ""),
        getprospect_api_key=req.getprospect_key or os.getenv("GETPROSPECT_API_KEY", ""),
        apollo_api_key=req.apollo_key or os.getenv("APOLLO_API_KEY", ""),
        snov_api_key=req.snov_key or os.getenv("SNOV_API_KEY", ""),
        progress_log=progress_log,
    )

    return {
        "job_data": job_data,
        "research_data": research_data,
        "best_email": best_email,
        "source": source,
        "all_contacts": all_contacts,
        "log": progress_log,
    }


# ── Tailor Resume ──────────────────────────────────────────────────────

@app.post("/api/tailor-resume")
async def tailor_resume_endpoint(req: TailorResumeRequest):
    try:
        tailored = tailor_resume(
            resume_text=req.resume_text,
            job_description=req.job_description,
            company_name=req.company_name or "",
            api_keys={
                "groq_key": req.groq_key,
                "fireworks_key": req.fireworks_key
            }
        )
        return {"tailored_resume": tailored}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Tailor LaTeX Resume ────────────────────────────────────────────────

@app.post("/api/tailor-latex")
async def tailor_latex_endpoint(req: TailorLatexRequest):
    try:
        # LLM tailoring of source
        tailored_tex = tailor_latex_resume(
            latex_source=req.latex_source,
            job_description=req.job_description,
            company_name=req.company_name or "",
            company_research=req.company_research or "",
            api_keys={
                "groq_key": req.groq_key,
                "fireworks_key": req.fireworks_key
            }
        )
        
        # Compile using pdflatex in a temp dir
        with tempfile.TemporaryDirectory() as temp_dir:
            tex_path = os.path.join(temp_dir, "resume.tex")
            with open(tex_path, "w") as f:
                f.write(tailored_tex)
            
            # Check availability: try tectonic first (faster, self-contained), fallback to pdflatex
            if shutil.which("tectonic"):
                compile_cmd = ["tectonic", "resume.tex"]
            elif shutil.which("pdflatex"):
                compile_cmd = ["pdflatex", "-interaction=nonstopmode", "resume.tex"]
            else:
                raise HTTPException(status_code=500, detail="No LaTeX compiler found. Please 'brew install tectonic'.")
                
            process = subprocess.run(
                compile_cmd,
                cwd=temp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            pdf_path = os.path.join(temp_dir, "resume.pdf")
            if process.returncode != 0 or not os.path.exists(pdf_path):
                raise HTTPException(status_code=500, detail=f"LaTeX compilation failed:\n{process.stdout.decode()}")
                
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
                
            return Response(content=pdf_bytes, media_type="application/pdf")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Generate Email ─────────────────────────────────────────────────────

@app.post("/api/generate-email")
async def generate_email_endpoint(req: GenerateEmailRequest):
    try:
        subject, body = generate_reply(
            resume=req.resume_text,
            job_description=req.job_description,
            company_name=req.company_name,
            company_research=req.company_research,
            recruiter_name=req.recruiter_name,
            additional_context=req.additional_context,
            user_name=req.user_name,
            user_email=req.user_email,
            linkedin_url=req.linkedin_url,
            institution=req.institution,
            api_keys={
                "groq_key": req.groq_key,
                "fireworks_key": req.fireworks_key
            }
        )
        
        if req.job_url:
            body = body.strip() + f"\n\nHere is the LinkedIn job posting that I am referencing:\n{req.job_url}"
            
        return {"subject": subject, "body": body}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Send Email ─────────────────────────────────────────────────────────

@app.post("/api/send-email")
async def send_mail_endpoint(
    background_tasks: BackgroundTasks,
    to_emails: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    access_token: Optional[str] = Form(None),
    resume_file: Optional[UploadFile] = File(None),
    resume_bucket_uri: Optional[str] = Form(None),
    contacts_json: Optional[str] = Form(None),
):
    """Send emails — via Gmail OAuth if access_token provided, else SMTP fallback."""
    emails = [e.strip() for e in to_emails.split(",") if e.strip()]
    if not emails:
        raise HTTPException(status_code=400, detail="No email addresses provided.")

    attachment_bytes = None
    attachment_name = "resume.pdf"
    
    if resume_file:
        attachment_bytes = await resume_file.read()
        attachment_name = resume_file.filename
    elif resume_bucket_uri:
        from utils.db import supabase
        if supabase:
            try:
                res = supabase.storage.from_("resumes").download(resume_bucket_uri)
                attachment_bytes = res
                attachment_name = "resume.pdf"
            except Exception as e:
                print(f"Bucket download failed: {e}")

    # Build contacts map from JSON
    import json
    import re
    contacts_map = {}
    if contacts_json:
        try:
            parsed = json.loads(contacts_json)
            for c in parsed:
                em = c.get("email")
                if em:
                    contacts_map[em.lower().strip()] = c.get("name", "")
        except Exception as e:
            print(f"Failed to parse contacts_json: {e}")

    if access_token:
        # Use Gmail API with user's OAuth token
        from utils.email_sender import send_email_gmail_api
        import time

        def _send_oauth():
            for email_addr in emails:
                custom_body = body
                c_name = contacts_map.get(email_addr.lower(), "")
                first_name = c_name.split()[0] if c_name else ""
                greeting = f"Hi {first_name}," if first_name else "Hi there,"
                custom_body = re.sub(r"^Hi\s.*?,", greeting, custom_body, flags=re.MULTILINE)

                send_email_gmail_api(
                    to=email_addr,
                    subject=subject,
                    body=custom_body,
                    access_token=access_token,
                    attachment_bytes=attachment_bytes,
                    attachment_name=attachment_name,
                )
                if len(emails) > 1:
                    time.sleep(10)

        background_tasks.add_task(_send_oauth)
    else:
        # Fallback to SMTP
        import time

        def _send_smtp():
            for email_addr in emails:
                custom_body = body
                c_name = contacts_map.get(email_addr.lower(), "")
                first_name = c_name.split()[0] if c_name else ""
                greeting = f"Hi {first_name}," if first_name else "Hi there,"
                custom_body = re.sub(r"^Hi\s.*?,", greeting, custom_body, flags=re.MULTILINE)

                send_email(
                    to=email_addr,
                    subject=subject,
                    body=custom_body,
                    attachment_bytes=attachment_bytes,
                    attachment_name=attachment_name,
                )
                if len(emails) > 1:
                    time.sleep(10)

        background_tasks.add_task(_send_smtp)

    return {"message": f"Emails queued for {len(emails)} recipient(s)."}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
