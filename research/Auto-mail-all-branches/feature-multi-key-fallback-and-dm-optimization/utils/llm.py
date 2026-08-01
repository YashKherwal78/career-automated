"""LLM-based email reply and LinkedIn DM generator using Groq."""
import os
import logging
from groq import Groq, RateLimitError, APIStatusError, APIConnectionError, GroqError
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

EMAIL_SYSTEM_PROMPT_TEMPLATE = """You are an expert career coach and professional email writer for {user_name}.
Your job is to draft a concise, warm, and highly personalized job application reply email.

STRICT OUTPUT FORMAT — follow exactly (plain text only, no markdown):
SUBJECT: <a specific, context-aware subject line mentioning the role and company>

Hi <recruiter first name if mentioned, otherwise "there">,

<2-4 short paragraphs:
 - Express genuine, specific interest in the role and company. Use the provided company research to sound highly informed and personalized.
 - Mention that you are a graduate/alumnus of the Indian Institute of Technology, Roorkee (IIT Roorkee) — use the full institutional name naturally to establish credibility, e.g. "As a graduate of the Indian Institute of Technology, Roorkee (IIT Roorkee)" or "As an alumnus of IIT Roorkee". Do NOT say you are a current student.
 - Highlight how 2-3 specific skills from the resume directly match the job requirements
 - Mention "my resume is attached for your reference"
 - End with a clear call to action (e.g., happy to schedule a call)>

Thank you for your time and consideration.

Best regards,
{user_name}
LinkedIn: {linkedin_url}

RULES:
- Plain text only — no asterisks, no markdown, no bullet points with dashes or stars, no bold/italic formatting
- Do NOT use "I hope this email finds you well" or any generic filler
- Keep it 150-250 words (body only, not counting salutation/sign-off)
- The IIT Roorkee mention must feel organic and add credibility, not forced
- {extra_rules}
- Be confident and specific"""

RISHABH_EMAIL_SYSTEM_PROMPT_TEMPLATE = """You are an expert career coach writing for Rishabh Jain. Follow this EXACT STRUCTURE and phrasing. Do NOT change the core bullet points drastically, just tailor them slightly to align with the company's tech/focus. DO NOT USE MARKDOWN (NO BOLD/ITALIC unless explicitly asked). Use bullet point symbol (•). 

SUBJECT: <specific, context-aware subject line mentioning role and company>

Hi <recruiter name if provided, else "there">,

I came across the <Job Title> opening at <Company Name> and wanted to reach out, the intersection of <Company Domain 1> and <Company Domain 2> is exactly the space I've been building in.

What <Company Name> is solving resonates with me deeply: <1 short sentence about how their product/mission solves a data/AI/engineering problem>. Having worked on agentic RAG pipelines, connector integrations, and LLM-powered workflows, I understand the complexity of <Company's key technical challenge>. A few things from my background that I think align well:

• **At UnifyApps**, I built production-grade connectors (Microsoft Planner, Slack, Google Drive, Calendar) with OAuth 2.0, paginated Graph API traversal, and stateful workflow automation directly relevant to <Company Name>'s <ecosystem/needs>.
• **At Pepsales**, I built an agentic RAG pipeline end-to-end ingesting B2B SaaS call transcripts, applying map-reduce summarization, and achieving ~25x retrieval speedup via binary embedding quantization. Optimizing retrieval pipelines for production is something I enjoy deeply.
• **At Turing**, I've worked on RLHF-based fine-tuning (LoRA/QLoRA) for Anthropic's and Amazon's foundation models so I understand model behavior at a level that goes beyond prompting.
<OPTIONAL: If the prompt's resume or additional context mentions something strictly matching another major requirement, add exactly 1 more bullet point here. OTHERWISE DO NOT ADD ANYTHING.>

<OPTIONAL: 1 very short closing sentence if there's an exact match in the JD that you must mention> I'd love to explore if there's a fit.

My LinkedIn: https://www.linkedin.com/in/rishabh-jain1603/
I've attached my resume for reference. Thank you for your time looking forward to hearing from you.

Best,
Rishabh Jain
+91-9871522382

RULES:
- Use **bold** formatting for the company names at the start of bullet points exactly as shown above in the example, but avoid excessive markdown elsewhere.
- Do NOT mention IIT Roorkee as your work experience. 
- Ensure the exact mobile number and LinkedIn link are preserved at the bottom!
"""

PRIYA_EMAIL_SYSTEM_PROMPT_TEMPLATE = """You are an expert career coach writing for Priya Rajput. Follow this EXACT STRUCTURE and phrasing. Do NOT change the core bullet points drastically, just tailor them slightly to align with the company's tech/focus. DO NOT USE MARKDOWN (NO BOLD/ITALIC unless explicitly asked). Use bullet point symbol (•). 

SUBJECT: <specific, context-aware subject line mentioning role and company>

Hi <recruiter name if provided, else "there">,

I came across the <Job Title> opening at <Company Name> and wanted to reach out, the intersection of <Company Domain 1> and <Company Domain 2> is exactly the space I've been building in.

What <Company Name> is solving resonates with me deeply: <1 short sentence about how their product/mission solves a data/AI/analytics problem>. Having worked on AI training pipelines, predictive modeling, and data-driven product analytics, I understand the complexity of <Company's key technical/product challenge>. A few things from my background that I think align well:

• **At Outlier**, I worked on RLHF and SFT pipelines to improve the reasoning and STEM capabilities of large language models, designing high-quality training data and evaluating AI-generated responses for accuracy directly relevant to <Company Name>'s <ecosystem/needs>.
• **At IIT Roorkee's Physics Department**, I built deep feedforward networks using PyTorch and TensorFlow to predict beta decay half-lives, developing custom GPU-accelerated training pipelines and optimizing hyperparameters to achieve <5% MAPE. Optimizing model architectures and pipelines is something I enjoy deeply.
• **At Enactus (Wings R Us & Myntra projects)**, I built a real-time AI recommendation system achieving a 35% CTR and 0.90 Recall, and designed data-driven frameworks to reduce cart abandonment—so I understand product analytics and model deployment at a level that goes beyond baseline modeling.
<OPTIONAL: If the prompt's resume or additional context mentions something strictly matching another major requirement, add exactly 1 more bullet point here. OTHERWISE DO NOT ADD ANYTHING.>

<OPTIONAL: 1 very short closing sentence if there's an exact match in the JD that you must mention> I'd love to explore if there's a fit.

My LinkedIn: https://www.linkedin.com/in/priya-rajput04/
I've attached my resume for reference. Thank you for your time looking forward to hearing from you.

Best,
Priya Rajput
+91-9311984857

RULES:
- Use **bold** formatting for the company names at the start of bullet points exactly as shown above in the example, but avoid excessive markdown elsewhere.
- Ensure the exact mobile number and LinkedIn link are preserved at the bottom!
"""

LINKEDIN_SYSTEM_PROMPT_TEMPLATE = """You are a LinkedIn messaging expert for {user_name} from the Indian Institute of Technology, Roorkee (IIT Roorkee).
Write a SHORT, friendly LinkedIn DM (100-130 words max) to a recruiter about a job opportunity.

STRICT OUTPUT FORMAT (plain text, no markdown):
Hi <recruiter first name if mentioned, otherwise "there">,

<2-3 short paragraphs:
 - Briefly introduce yourself as an IIT Roorkee graduate/alumnus, reference the specific role/company, and touch on any provided company research lightly. Do NOT refer to yourself as a student.
 - Highlight 1-2 top-matching skills from the resume
 - Mention "I have also sent my resume for your reference"
 - End with a friendly call to action>

Looking forward to connecting!

{user_name}
LinkedIn: {linkedin_url}

RULES:
- Conversational yet professional tone
- Max 130 words total
- No generic openers
- {extra_rules}
- Plain text only — no markdown, no bullet symbols, no bold/italic"""


def extract_job_details(raw_text: str) -> dict:
    """Use an LLM to accurately extract structured details from messy HTML text."""
    system_prompt = (
        "You are a strict data extraction assistant. Given raw text from a job posting, "
        "extract the standard fields into a clean JSON object.\n\n"
        "Return ONLY a valid JSON object with EXACTLY the following string keys. "
        "If a value is not found, use null.\n"
        "- company_name\n"
        "- job_title (the exact, true job title, which is usually found at the very beginning of the webpage text)\n"
        "- job_description (the core responsibilities and requirements)\n"
        "- recruiter_name (if a specific person is mentioned as a point of contact)\n"
        "- recruiter_email (extract the exact email address if present, with no modifications)"
    )
    
    try:
        response = _run_with_fallback(
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Extract from this text:\n\n{raw_text}"},
            ],
            temperature=0.1,
            max_tokens=1000,
        )
        import json
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"LLM extraction failed: {e}")
        return {}


# ── Round-robin key state file ────────────────────────────────────────────────
_KEY_STATE_FILE = os.path.join(os.path.dirname(__file__), "..", ".groq_key_state")


def _get_api_keys() -> list[str]:
    """Collect all configured GROK/GROQ API keys, preserving order."""
    keys = []
    # Try the numbered multi-key setup
    for prefix in ["GROK_API_", "GROQ_API_"]:
        for i in range(1, 10):
            key = os.getenv(f"{prefix}{i}")
            if not key and hasattr(st, "secrets"):
                try:
                    key = st.secrets.get(f"{prefix}{i}")
                except Exception:
                    pass
            if key and key not in keys:
                keys.append(key)

    # Fallback to single GROQ_API_KEY / GROK_API_KEY
    if not keys:
        for single in ["GROQ_API_KEY", "GROK_API_KEY"]:
            key = os.getenv(single)
            if not key and hasattr(st, "secrets"):
                try:
                    key = st.secrets.get(single)
                except Exception:
                    pass
            if key and key not in keys:
                keys.append(key)

    if not keys:
        raise ValueError("No GROQ/GROK API keys found in .env or secrets.")

    return keys


def _read_last_key_index() -> int:
    """Read the last-used key index from the state file. Returns 0 if missing."""
    try:
        with open(_KEY_STATE_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return 0


def _write_last_key_index(idx: int) -> None:
    """Persist the last successfully used key index."""
    try:
        with open(_KEY_STATE_FILE, "w") as f:
            f.write(str(idx))
    except Exception:
        pass  # non-critical


def _run_with_fallback(**kwargs):
    """Round-robin key rotation with automatic fallback on errors.

    Starts from the key AFTER the last successfully used one (1→2→3→1…).
    On error (rate limit / credit exhaustion / server error), advances to
    the next key.  Persists state to `.groq_key_state` so rotation survives
    across app restarts.
    """
    keys = _get_api_keys()
    n = len(keys)
    last_idx = _read_last_key_index()
    start_idx = (last_idx + 1) % n          # begin from NEXT key
    last_error = None

    for attempt in range(n):
        idx = (start_idx + attempt) % n
        api_key = keys[idx]
        try:
            client = Groq(api_key=api_key)
            result = client.chat.completions.create(**kwargs)
            _write_last_key_index(idx)       # remember successful key
            logging.getLogger(__name__).info(f"API call succeeded on key {idx+1}/{n}")
            return result
        except RateLimitError as e:
            logging.getLogger(__name__).warning(
                f"Rate limit hit on API key {idx+1}/{n}. Trying next...")
            last_error = e
        except APIStatusError as e:
            if e.status_code in (402, 429, 500, 502, 503, 504):
                logging.getLogger(__name__).warning(
                    f"API Error ({e.status_code}) on key {idx+1}/{n}. Trying next...")
                last_error = e
            else:
                raise e  # 400 / prompt errors – don't waste other keys
        except APIConnectionError as e:
            logging.getLogger(__name__).warning(
                f"Connection error on key {idx+1}/{n}. Trying next...")
            last_error = e
        except GroqError as e:
            logging.getLogger(__name__).warning(
                f"Groq API error on key {idx+1}/{n}. Trying next...")
            last_error = e
        except Exception as e:
            logging.getLogger(__name__).error(
                f"Unexpected error on key {idx+1}/{n}: {e}. Trying next...")
            last_error = e

    # All keys exhausted
    if last_error:
        logging.getLogger(__name__).error("All API keys exhausted. Final failure.")
        raise last_error


def _build_user_message(
    resume: str, 
    job_description: str,
    company_name: str,
    company_research: str,
    additional_context: str,
    recruiter_name: str = ""
) -> str:
    """Helper to structure the user input for the LLM."""
    msg = []
    if company_name:
        msg.append(f"## Target Company\n{company_name}\n")
    if company_research:
        msg.append(f"## Company Research Context\n{company_research}\n")
    if recruiter_name:
        msg.append(f"## Recruiter Name\n{recruiter_name}\n")
    if job_description:
        msg.append(f"## Job Description\n{job_description}\n")
    if additional_context:
        msg.append(f"## Additional User Context (Notes/Instructions)\n{additional_context}\n")
    if resume:
        msg.append(f"## My Resume\n{resume}\n")
        
    msg.append("Please write the reply following the strict format.")
    return "\n".join(msg)


def generate_reply(
    resume: str = "",
    job_description: str = "",
    company_name: str = "",
    company_research: str = "",
    recruiter_name: str = "",
    additional_context: str = "",
    user_name: str = "Priya Rajput",
    linkedin_url: str = "https://www.linkedin.com/in/priya-rajput04/",
    institution: str = "IIT Roorkee",
) -> tuple[str, str]:
    """Generate a tailored reply email.

    Returns:
        Tuple of (subject, body).
    """
    extra_rules = "Focus prominently on actual WORK EXPERIENCE from the resume that closely aligns with the job description."
    if "Rishabh" in user_name:
        system_prompt = RISHABH_EMAIL_SYSTEM_PROMPT_TEMPLATE
    elif "Priya" in user_name:
        system_prompt = PRIYA_EMAIL_SYSTEM_PROMPT_TEMPLATE
    else:
        system_prompt = EMAIL_SYSTEM_PROMPT_TEMPLATE.format(
            user_name=user_name,
            linkedin_url=linkedin_url,
            institution=institution,
            extra_rules=extra_rules
        )

    user_message = _build_user_message(
        resume=resume,
        job_description=job_description,
        company_name=company_name,
        company_research=company_research,
        additional_context=additional_context,
        recruiter_name=recruiter_name,
    )

    response = _run_with_fallback(
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


def generate_linkedin_dm(
    resume: str = "",
    job_description: str = "",
    company_name: str = "",
    company_research: str = "",
    recruiter_name: str = "",
    additional_context: str = "",
    user_name: str = "Priya Rajput",
    linkedin_url: str = "https://www.linkedin.com/in/priya-rajput04/",
    institution: str = "IIT Roorkee",
) -> str:
    """Generate a short LinkedIn DM for the recruiter."""
    extra_rules = "Focus prominently on actual WORK EXPERIENCE from the resume that closely aligns with the job description."
    if "Rishabh" in user_name:
        extra_rules += " Do NOT use IIT Roorkee as work experience or project experience; only mention being an IIT Roorkee graduate for credibility."

    system_prompt = LINKEDIN_SYSTEM_PROMPT_TEMPLATE.format(
        user_name=user_name,
        linkedin_url=linkedin_url,
        institution=institution,
        extra_rules=extra_rules
    )

    user_message = _build_user_message(
        resume=resume,
        job_description=job_description,
        company_name=company_name,
        company_research=company_research,
        additional_context=additional_context,
        recruiter_name=recruiter_name,
    )

    response = _run_with_fallback(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.75,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()
