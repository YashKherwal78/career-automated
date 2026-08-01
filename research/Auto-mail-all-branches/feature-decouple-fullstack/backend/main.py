from __future__ import annotations
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
import requests as http_requests

from utils.scraper import parse_job_url, research_company, enrich_recruiter_email
from utils.llm import generate_reply, generate_linkedin_dm
from utils.email_sender import send_email

# Load .env
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="ApplyWithAI API", version="2.0.0")

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
    return {"status": "ok", "service": "applywith-ai-api", "version": "2.0.0"}


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


# ── Models ─────────────────────────────────────────────────────────────

class PipelineRequest(BaseModel):
    job_url: Optional[str] = ""
    additional_context: Optional[str] = ""
    hunter_key: Optional[str] = ""
    getprospect_key: Optional[str] = ""

class GenerateEmailRequest(BaseModel):
    resume_text: str
    job_description: str
    company_name: str
    company_research: str
    recruiter_name: Optional[str] = ""
    additional_context: Optional[str] = ""
    user_name: str
    linkedin_url: str
    institution: str


# ── PDF Parse ──────────────────────────────────────────────────────────

from utils.pdf_reader import extract_text_from_pdf

@app.post("/api/parse-pdf")
async def parse_pdf(file: UploadFile = File(...)):
    try:
        content = await file.read()
        text = extract_text_from_pdf(content)
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Pipeline ───────────────────────────────────────────────────────────

@app.post("/api/pipeline")
async def run_pipeline(req: PipelineRequest):
    """Parses URL, researches company, and finds contacts."""
    job_data = {}
    if req.job_url:
        job_data = parse_job_url(req.job_url.strip())
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
            linkedin_url=req.linkedin_url,
            institution=req.institution,
        )
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

    if access_token:
        # Use Gmail API with user's OAuth token
        from utils.email_sender import send_email_gmail_api
        import time

        def _send_oauth():
            for email_addr in emails:
                send_email_gmail_api(
                    to=email_addr,
                    subject=subject,
                    body=body,
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
                send_email(
                    to=email_addr,
                    subject=subject,
                    body=body,
                    attachment_bytes=attachment_bytes,
                    attachment_name=attachment_name,
                )
                if len(emails) > 1:
                    time.sleep(10)

        background_tasks.add_task(_send_smtp)

    return {"message": f"Emails queued for {len(emails)} recipient(s)."}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
