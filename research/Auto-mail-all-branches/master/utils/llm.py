"""LLM-based email reply generator using Groq."""
import os
from groq import Groq
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

EMAIL_SYSTEM_PROMPT = """You are an expert career coach and professional email writer for Priya Rajput.
Your job is to draft a concise, warm, and highly personalized job application reply email.

STRICT OUTPUT FORMAT — follow exactly:
SUBJECT: <a specific, context-aware subject line mentioning the role and company if identifiable>

Hi <recruiter first name if mentioned, otherwise "there">,

<2-4 short paragraphs:
 - Express genuine, specific interest in the role
 - Highlight 2-3 relevant strengths from the resume that directly match the job requirements
 - Mention "my resume is attached for your reference"
 - End with a clear call to action (e.g., happy to schedule a call)>

Thank you for your time and consideration.

Best regards,
Priya Rajput

RULES:
- Do NOT use "I hope this email finds you well" or any generic filler
- Keep it 150-220 words (body only, not counting salutation/sign-off)
- Be confident and specific, not generic"""

LINKEDIN_SYSTEM_PROMPT = """You are a LinkedIn messaging expert for Priya Rajput.
Write a SHORT, friendly LinkedIn DM (100-130 words max) to a recruiter about a job opportunity.

STRICT OUTPUT FORMAT:
Hi <recruiter first name if mentioned, otherwise "there">,

<2-3 short paragraphs:
 - Briefly introduce yourself and reference the specific role/company
 - Highlight 1-2 top-matching skills from the resume
 - Mention "I've also attached my resume for your reference" 
 - End with a friendly call to action>

Looking forward to connecting!
Priya Rajput

RULES:
- Conversational yet professional tone
- Max 130 words
- No generic openers like "I hope this finds you well"
- Do NOT include subject lines"""


def _get_client() -> Groq:
    api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is not set. Add it to .streamlit/secrets.toml or your .env file."
        )
    return Groq(api_key=api_key)


def generate_reply(resume: str, jd: str) -> tuple[str, str]:
    """Generate a tailored reply email.

    Returns:
        Tuple of (subject, body) where body includes salutation and sign-off.
    """
    client = _get_client()

    user_message = f"""## Recruiter Email / Job Description
{jd}

## My Resume
{resume}

Please write the reply email following the strict format."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": EMAIL_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
        max_tokens=700,
    )
    raw = response.choices[0].message.content.strip()

    # Parse SUBJECT: line from response
    subject = "Re: Job Opportunity"
    body = raw
    if raw.startswith("SUBJECT:"):
        lines = raw.split("\n", 2)
        subject = lines[0].replace("SUBJECT:", "").strip()
        body = "\n".join(lines[1:]).strip()

    return subject, body


def generate_linkedin_dm(resume: str, jd: str) -> str:
    """Generate a short LinkedIn DM for the recruiter."""
    client = _get_client()

    user_message = f"""## Recruiter / Job Info
{jd}

## My Resume
{resume}

Please write the LinkedIn DM following the strict format."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": LINKEDIN_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.75,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()
