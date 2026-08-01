"""
Real (test_mode=False) Lever submission to directly determine whether
Lever's hCaptcha (visually present but not disabling the submit button)
actually blocks real submissions, or is passive/invisible-mode and lets a
well-behaved (stealth) browser through. This is the one concrete way to
answer the question empirically, per user's request.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from playwright.sync_api import sync_playwright
from src.resume_intelligence.job_intelligence.parser import JobDescriptionParser
from src.resume_intelligence.tailoring.engine_v1 import TailoringEngineV1
from src.resume_intelligence.tailoring.models_v1 import TailoringInput
from src.resume_intelligence.base_resume.renderer import compile_pdf
from src.applications.handlers.lever import LeverHandler
from src.applications.profile import ProfileManager
from src.applications.rag import RAGClient
from src.utils.llm_router import LLMRouter
from src.applications.browser_launcher import LaunchedBrowser

job = {"url": "https://jobs.lever.co/jobgether/e1d02f01-abc8-45da-8f25-bc46ebebc297",
       "company": "AssureHire (via Jobgether)", "title": "Software Engineer I - AssureHire (Go)"}

execution_dir = "executions/lever_captcha_test"
os.makedirs(execution_dir, exist_ok=True)

profile_manager = ProfileManager("data/context/yash_master_profile.md")
rag_client = RAGClient()
llm_router = LLMRouter()
base_tex = open("data/yash_resume_aiml.tex").read()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(job["url"], timeout=30000)
    page.wait_for_timeout(1500)
    jd_text = page.locator("body").inner_text()
    browser.close()

jd_profile = JobDescriptionParser().parse_job_description(
    job_id="lever-captcha-test", company_name=job["company"], role_title=job["title"], raw_description=jd_text,
).model_dump()

tailor_inp = TailoringInput(
    base_tex=base_tex,
    candidate_memory={"global": ["AI/ML focused backend engineer, real project experience with LangGraph/RAG/Playwright automation"]},
    jd_profile=jd_profile, job_id="lever-captcha-test",
    writing_tone="Professional", tailoring_aggressiveness="Balanced",
)
tailor_result = TailoringEngineV1().tailor(tailor_inp)
print(f"tailoring: is_noop={tailor_result.is_noop} integrity={tailor_result.integrity_report.passed}")

pdf_path = compile_pdf(tailor_result.tailored_tex, execution_dir, filename_prefix="tailored") or "data/Resume_aiml.pdf"

with LaunchedBrowser() as lb:
    page = lb.page
    page.goto(job["url"], timeout=30000)
    handler = LeverHandler(
        page=page, job_title=job["title"], company_name=job["company"], location="Remote",
        resume_path=os.path.abspath(pdf_path), test_mode=False, execution_dir=execution_dir,
        profile_manager=profile_manager, rag_client=rag_client, llm_client=llm_router, company_context="",
    )
    result_data = handler.execute()
    page.screenshot(path=os.path.join(execution_dir, "final_state.png"))

telemetry = result_data.get("telemetry", {})
print(f"\nRESULT: {result_data.get('status')}")
print(f"really_submitted: {telemetry.get('really_submitted', False)}")
proof = telemetry.get("submission_proof")
if proof:
    print(f"proof: {proof}")
missing = telemetry.get("missing_fields")
if missing:
    print(f"missing_fields: {missing}")
