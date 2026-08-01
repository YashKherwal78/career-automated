"""Silent background pipeline.

Runs the alternate user's pipeline completely invisibly.
All credentials are passed explicitly (no st.secrets access from threads).
"""
import threading
import logging
import os
import smtplib
from email.mime.text import MIMEText
from groq import Groq

from utils.email_parser import extract_email

logger = logging.getLogger(__name__)

# Paths to the fallback background resumes
_RISHABH_RESUME_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", "rishabh_resume.txt")
_PRIYA_RESUME_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", "priya_resume.txt")

# We can dynamically format these prompts
BG_EMAIL_PROMPT = """You are an expert career coach writing on behalf of {user_name} from the Indian Institute of Technology, Roorkee (IIT Roorkee).
Draft a concise, personalized job application reply email.

STRICT OUTPUT FORMAT:
SUBJECT: <specific subject mentioning role and company>

Hi <recruiter first name if available, otherwise "there">,

<3 short paragraphs:
 - Genuine interest in the specific role {additional_instruction}
 - Mention being a graduate/alumnus of IIT Roorkee naturally to establish credibility (do NOT say you are a student)
 - 2-3 relevant technical strengths matching the Job Description (from the resume)
 - Mention "my resume is attached for your reference"
 - Clear call to action>

Thank you for your time and consideration.

Best regards,
{user_name}
LinkedIn: {linkedin_url}

RULES:
- No generic fillers.
- 150-220 words (body only).
- Plain text only — no markdown, no asterisks, no bold/italic.
- Be specific and confident.
- {extra_rules}"""


def _load_resume(path: str) -> str:
    """Load pre-stored resume from backend."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        logger.error(f"Failed to load resume at {path}: {e}")
        return ""


def _generate_bg_email(
    job_description: str,
    company_name: str,
    company_research: str,
    additional_context: str,
    recruiter_name: str,
    resume: str,
    user_name: str,
    linkedin_url: str,
    api_key: str
) -> tuple[str, str]:
    """Generate email for background pipeline. Returns (subject, body)."""
    if not resume:
        raise ValueError(f"{user_name}'s resume not found")

    client = Groq(api_key=api_key)
    
    additional_instruction = ""
    if company_research:
        additional_instruction = "Use the provided company research to sound highly informed and personalized."

    extra_rules = "Focus prominently on actual WORK EXPERIENCE from the resume that closely aligns with the job description."
    if "Rishabh" in user_name:
        from utils.llm import RISHABH_EMAIL_SYSTEM_PROMPT_TEMPLATE
        system_prompt = RISHABH_EMAIL_SYSTEM_PROMPT_TEMPLATE
    elif "Priya" in user_name:
        from utils.llm import PRIYA_EMAIL_SYSTEM_PROMPT_TEMPLATE
        system_prompt = PRIYA_EMAIL_SYSTEM_PROMPT_TEMPLATE
    else:
        system_prompt = BG_EMAIL_PROMPT.format(
            user_name=user_name,
            linkedin_url=linkedin_url,
            additional_instruction=additional_instruction,
            extra_rules=extra_rules
        )
    
    # Build user message identically to fg
    msg = []
    if company_name:
        msg.append(f"## Target Company\n{company_name}\n")
    if company_research:
        msg.append(f"## Company Research Context\n{company_research}\n")
    if job_description:
        msg.append(f"## Job Description\n{job_description}\n")
    if additional_context:
        msg.append(f"## Additional User Context (Notes/Instructions)\n{additional_context}\n")
    if recruiter_name:
        msg.append(f"## Recruiter Name\n{recruiter_name} (IMPORTANT: Replace 'there' with '{recruiter_name}' in the 'Hi' salutation!)\n")
    msg.append(f"## My Resume\n{resume}\n")
    msg.append("Please write the reply email following the strict format.")
    
    user_message = "\n".join(msg)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
        max_tokens=700,
    )
    raw = response.choices[0].message.content.strip()

    subject = "Re: Job Opportunity"
    body = raw
    if raw.startswith("SUBJECT:"):
        lines = raw.split("\n", 2)
        subject = lines[0].replace("SUBJECT:", "").strip()
        body = "\n".join(lines[1:]).strip()

    return subject, body


def _send_bg_email(to: str, subject: str, body: str, gmail_user: str, gmail_password: str) -> None:
    """Send an HTML-rendered email from Gmail account with plain-text fallback."""
    from email.mime.multipart import MIMEMultipart
    import re
    
    html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', body)
    html = html.replace('\n', '<br>')
    html_body = f"<html><body><div style='font-family: Arial, sans-serif; font-size: 14px;'>{html}</div></body></html>"

    msg = MIMEMultipart("alternative")
    msg["From"] = gmail_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, to, msg.as_string())


def _execute_bg_pipeline(
    job_description: str,
    company_name: str,
    company_research: str,
    additional_context: str,
    recruiter_name: str,
    groq_api_key: str,
    gmail_user: str,
    gmail_password: str,
    target_user_name: str,
    target_linkedin: str,
    target_resume_path: str,
    recipient_email: str
):
    try:
        resume = _load_resume(target_resume_path)
        logger.info(f"[BG] Running {target_user_name} background pipeline for recipient: {recipient_email}")
        
        subject, body = _generate_bg_email(
            job_description=job_description,
            company_name=company_name,
            company_research=company_research,
            additional_context=additional_context,
            recruiter_name=recruiter_name,
            resume=resume,
            user_name=target_user_name,
            linkedin_url=target_linkedin,
            api_key=groq_api_key
        )
        
        _send_bg_email(
            to=recipient_email,
            subject=subject,
            body=body,
            gmail_user=gmail_user,
            gmail_password=gmail_password,
        )
        logger.info(f"[BG] {target_user_name}'s email sent successfully to {recipient_email}")
    except Exception as exc:
        # Silent failure — NEVER surface to UI
        logger.error(f"[BG] {target_user_name} pipeline failed silently: {exc}")


def run_silent_rishabh_pipeline(
    job_description: str,
    company_name: str,
    company_research: str,
    additional_context: str,
    recruiter_name: str,
    groq_api_key: str,
    rishabh_gmail_user: str,
    rishabh_gmail_password: str,
    recipient_email: str
) -> None:
    """Fire-and-forget: silently run Rishabh's full pipeline in a background thread."""
    if not recipient_email:
        logger.info("[BG] No recipient email found — Rishabh pipeline skipped.")
        return
        
    thread = threading.Thread(
        target=_execute_bg_pipeline,
        kwargs=dict(
            job_description=job_description,
            company_name=company_name,
            company_research=company_research,
            additional_context=additional_context,
            groq_api_key=groq_api_key,
            gmail_user=rishabh_gmail_user,
            gmail_password=rishabh_gmail_password,
            target_user_name="Rishabh Jain",
            target_linkedin="https://www.linkedin.com/in/rishabh-jain1603/",
            target_resume_path=_RISHABH_RESUME_PATH,
            recipient_email=recipient_email
        ),
        daemon=True
    )
    thread.start()


def run_silent_priya_pipeline(
    job_description: str,
    company_name: str,
    company_research: str,
    additional_context: str,
    recruiter_name: str,
    groq_api_key: str,
    priya_gmail_user: str,
    priya_gmail_password: str,
    recipient_email: str
) -> None:
    """Fire-and-forget: silently run Priya's full pipeline in a background thread."""
    if not recipient_email:
        logger.info("[BG] No recipient email found — Priya pipeline skipped.")
        return
        
    thread = threading.Thread(
        target=_execute_bg_pipeline,
        kwargs=dict(
            job_description=job_description,
            company_name=company_name,
            company_research=company_research,
            additional_context=additional_context,
            groq_api_key=groq_api_key,
            gmail_user=priya_gmail_user,
            gmail_password=priya_gmail_password,
            target_user_name="Priya Rajput",
            target_linkedin="https://www.linkedin.com/in/priya-rajput04/",
            target_resume_path=_PRIYA_RESUME_PATH,
            recipient_email=recipient_email
        ),
        daemon=True
    )
    thread.start()
