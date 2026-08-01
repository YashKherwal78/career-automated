import os
import time
from dotenv import load_dotenv

load_dotenv()

# We need to compute total prompt tokens and completion tokens
TOTAL_PROMPT_TOKENS = 0
TOTAL_COMPLETION_TOKENS = 0
CALL_COUNT = 0

original_run_with_fallback = None

def mock_run_with_fallback(*args, **kwargs):
    global TOTAL_PROMPT_TOKENS, TOTAL_COMPLETION_TOKENS, CALL_COUNT
    import utils.llm
    res = original_run_with_fallback(*args, **kwargs)
    
    if hasattr(res, 'usage') and res.usage:
        pt = res.usage.prompt_tokens
        ct = res.usage.completion_tokens
        print(f"    -> [LLM Call {CALL_COUNT+1}] Prompt: {pt}, Completion: {ct}, Total: {pt+ct}")
        TOTAL_PROMPT_TOKENS += pt
        TOTAL_COMPLETION_TOKENS += ct
    CALL_COUNT += 1
    return res

def test_job(job_url, resume, test_name):
    global TOTAL_PROMPT_TOKENS, TOTAL_COMPLETION_TOKENS, CALL_COUNT
    
    TOTAL_PROMPT_TOKENS = 0
    TOTAL_COMPLETION_TOKENS = 0
    CALL_COUNT = 0
    
    import utils.llm
    from utils.scraper import parse_job_url, research_company
    
    print(f"\n======================================")
    print(f"Testing {test_name}")
    print(f"URL: {job_url}")
    print(f"======================================")
    
    print("1. Parsing Job URL...")
    job_data = parse_job_url(job_url)
    
    if not job_data:
        print("   FAILED to parse job data. Check URL or LinkedIn block.")
        return
        
    print(f"   Parsed Title: {job_data.get('job_title')}")
    print(f"   Parsed Company: {job_data.get('company_name')}")
    
    print("2. Fetching Company Research...")
    company_research = research_company(job_data.get('company_name', ''))
    
    print("3. Generating Email Reply...")
    subject, body = utils.llm.generate_reply(
        resume=resume,
        job_description=job_data.get('job_description', ''),
        company_name=job_data.get('company_name', ''),
        company_research=company_research,
        recruiter_name=job_data.get('recruiter_name', ''),
        user_name="Rishabh Jain",
        linkedin_url="https://www.linkedin.com/in/rishabhjain1603",
        institution="IIT Roorkee",
    )
    
    print("4. Generating LinkedIn DM...")
    dm = utils.llm.generate_linkedin_dm(
        resume=resume,
        job_description=job_data.get('job_description', ''),
        company_name=job_data.get('company_name', ''),
        company_research=company_research,
        recruiter_name=job_data.get('recruiter_name', ''),
        user_name="Rishabh Jain",
        linkedin_url="https://www.linkedin.com/in/rishabhjain1603",
        institution="IIT Roorkee",
    )
    
    print("\n--- TOKEN USAGE & BOTTLENECK ANALYSIS FOR THIS EMAIL ---")
    total_tokens = TOTAL_PROMPT_TOKENS + TOTAL_COMPLETION_TOKENS
    print(f"Total LLM Calls: {CALL_COUNT}")
    print(f"Total Prompt Tokens: {TOTAL_PROMPT_TOKENS}")
    print(f"Total Completion Tokens: {TOTAL_COMPLETION_TOKENS}")
    print(f"Total Tokens Used: {total_tokens}")
    
    print("\n--- Groq Target Limits ---")
    print("RPM (Requests Per Minute): 30")
    print("TPM (Tokens Per Minute)  : 12,000")
    
    max_emails_rpm = 30 / max(CALL_COUNT, 1)
    max_emails_tpm = 12000 / max(total_tokens, 1)
    
    # RPD = 1,000 requests per day
    # TPD = 100,000 tokens per day
    max_emails_rpd = 1000 / max(CALL_COUNT, 1)
    max_emails_tpd = 100000 / max(total_tokens, 1)
    
    print(f"\n--- Bottleneck Metrics (Emails per time period) ---")
    print(f"Based on RPM : ~{max_emails_rpm:.2f} emails / min")
    print(f"Based on TPM : ~{max_emails_tpm:.2f} emails / min")
    if max_emails_tpm < max_emails_rpm:
        print("-> BOTTLENECK PER MINUTE: TPM (Token Limit)")
    else:
        print("-> BOTTLENECK PER MINUTE: RPM (Request Limit)")
        
    print(f"Based on RPD : ~{max_emails_rpd:.2f} emails / day")
    print(f"Based on TPD : ~{max_emails_tpd:.2f} emails / day")
    if max_emails_tpd < max_emails_rpd:
        print("-> BOTTLENECK PER DAY: TPD (Token Limit)")
    else:
        print("-> BOTTLENECK PER DAY: RPD (Request Limit)")
        
    
    print("\n5. Sending Actual Email...")
    from utils.email_sender import send_email
    
    recipient_email = "rishabhjain1632004@gmail.com"  # The sender email used as target for testing
    run_user = os.getenv("RISHABH_GMAIL_USER")
    run_pass = os.getenv("RISHABH_GMAIL_APP_PASSWORD")
    
    try:
        send_email(
            to=recipient_email,
            subject=f"[TEST - {test_name}] {subject}",
            body=body,
            gmail_user_override=run_user,
            gmail_pass_override=run_pass,
        )
        print(f"   Email successfully sent to {recipient_email}")
    except Exception as e:
        print(f"   Failed to send email: {e}")
        
    print("======================================\n")

def run_all():
    import utils.llm
    global original_run_with_fallback
    original_run_with_fallback = utils.llm._run_with_fallback
    utils.llm._run_with_fallback = mock_run_with_fallback
    
    resume = '''Rishabh Jain
+91-9871522382 | rishabhjain.1632004@gmail.com | linkedin.com/in/rishabhjain1603 | Gurugram, Haryana, India
Areas of Interest
Backend Systems Design, Agentic AI, Optimised RAG Systems, ML Infrastructure & Optimization, Automation
Education
Indian Institute of Technology, Roorkee Roorkee, Uttarakhand, India
B.Tech., Engineering Physics | CGPA: 9.12/10 Oct 2022 – May 2026
Experience
UnifyApps Gurugram, Haryana, India
Product Engineering Intern May 2025 – Jul 2025
• Engineered a production-grade Microsoft Planner connector in Java (Quarkus) implementing OAuth 2.0
token exchange, and paginated Graph API traversal to reliably ingest user data at scale into UnifyApps platform.
• Designed stateful automation workflows with branching logic, retry mechanisms, and idempotent data
transformation steps using UnifyApps’ workflow engine, enabling enterprise clients to orchestrate cross-system data
pipelines without custom code.
• Integrated Slack, Google Drive, and Google Calendar APIs into the AI Agents runtime; built tool-call
handlers, validated against live sandboxes.
Turing Remote
LLM Training Engineer Jan 2025 – May 2025
• Designed high-complexity RLHF preference tasks in the coding domain for training Anthropic’s, Amazon’s,
and Microsoft’s foundation models, producing ranked response pairs and detailed rationales to steer models
toward production-ready, trustworthy AI coding assistants.
• Authored adversarial and edge-case prompts targeting code correctness, security, and reasoning depth; maintained
consistent annotation quality standards that shaped model policy updates across training cycles.
Pepsales Bengaluru, Karnataka, India
Backend / Machine Learning Intern Aug 2024 – Dec 2024
• Built the Discovery Copilot end-to-end: an agentic RAG pipeline that ingests B2B SaaS sales call transcripts,
extracts deal insights, and generates discovery questions via GPT-4o mini with map-reduce summarization chains.
• Migrated retrieval from LangChain to a custom OpenAI-based pipeline with Astra DB and metadata filtering;
applied binary (1-bit) quantization of float32 embeddings using Hamming Distance similarity search,
achieving a ∼25x retrieval speedup and ∼40% latency reduction.
• Fine-tuned GPT-4o mini via LoRA/QLoRA using an RLHF reward model trained on human-labeled
preference data, improving domain-specific response accuracy and contextual relevance.
• Deployed the inference service on AWS EC2 with MongoDB for persistence and AWS S3 for document storage,
maintaining a scalable and reliable production environment.
VJ Nucleus Kota, Rajasthan, India
Machine Learning Intern Apr 2024 – Jun 2024
• Fine-tuned BERT on a self-constructed JEE question-chapter dataset, achieving 98.6% classification accuracy
for automated question categorization across subjects and chapters.
• Engineered a student-performance-driven DPP generation system leveraging analytics to personalize practice
problems, increasing student engagement by 40% and reducing manual curation effort by 25 hours/week.
Projects
ApplyWithAI | Llama 3.3 70B, Groq, Streamlit, LaTeX, SMTP Jan 2025
• Built an AI job application copilot using Llama 3.3 70B via Groq that generates tailored cold emails by
matching job description requirements against parsed resume data, cutting application time by ∼80%.
• Dynamically generates ATS-friendly resumes per job posting by incorporating role-specific requirements and
company-level insights (tech stack, culture); LLM outputs structured LaTeX, which a custom Python script
compiles and renders into professionally formatted, job-ready resumes.
• Implemented a parallel background pipeline for automated multi-application dispatch via Gmail SMTP with
resume attachments; supports multiple user profiles with user-specific personalization and contextual messaging.
Automated Memer | Reddit API, Microsoft TTS, Flask, SQLAlchemy Sep 2024
• Automated short-video generation from Reddit posts using Microsoft TTS (Hugging Face), Pillow, Pydub, and
FFMPEG; integrated Google OAuth v2, achieving an 80% reduction in content creation time | Demo video.
Nuclear Half-Life Prediction | Deep Learning, PyTorch, k-Fold CV Mar 2024
• Developed a deep learning framework to predict alpha-decay half-lives from nuclear properties (Z, A, Q),
achieving R2 = 0.92 and 3× lower RMSE than physics-based models (Geiger-Nuttall, Royer).
• Applied k-fold cross-validation, early stopping, and model checkpointing; preprocessed NuDat3 datasets with
logarithmic transformations and feature normalization, achieving MAE = 1.58 on held-out test data.
LangChain AI Chatbot | RAG, OpenAI, Astra DB, Django, React Dec 2023
• Built a RAG-based chatbot for IIT Roorkee using OpenAI embeddings and Astra DB as vector store;
chunked multi-source documents at 1000-char size with 300-char overlap, then applied semantic search via
LangChain for contextually precise retrieval.
• Engineered a Django REST backend with serialized API endpoints serving embedding queries, and a React
frontend with component-level state management and async fetch hooks for real-time response rendering.
Achievements
• Achieved AIR 4486 in JEE Advanced 2022.
• Achieved AIR 6867 (99.3 percentile) in JEE Mains 2022.
Technical Skills
Languages: Python, Java, C++, JavaScript
Frameworks: Django, Flask, FastAPI, Quarkus, React, PyTorch
Machine Learning & LLMs: OpenAI Framework, RLHF, LoRA/QLoRA, BERT, LangChain, Astra DB
DevOps: AWS (EC2, S3), Git, Docker, Vercel, Render'''
    
    url1 = "https://www.linkedin.com/jobs/search/?currentJobId=4394414595&f_TPR=r3600&origin=JOB_SEARCH_PAGE_JOB_FILTER"
    url2 = "http://linkedin.com/jobs/search/?currentJobId=4394405841&f_TPR=r3600&origin=JOB_SEARCH_PAGE_JOB_FILTER"
    
    test_job(url1, resume, "Input Data 1")
    
    # Wait lightly between full suite to not hammer LinkedIn limit
    time.sleep(2)
    
    test_job(url2, resume, "Input Data 2")

if __name__ == "__main__":
    run_all()
