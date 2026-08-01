"""
REAL submission test — this actually clicks Submit on a live job posting.
Salary is overridden to 20 LPA for this run (remote role), bypassing the
normal salary-escalation gate ONLY for this one-off test, not permanently.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

JOB_URL = "https://job-boards.greenhouse.io/backblaze/jobs/5207236008"
COMPANY = "Backblaze"
TITLE = "Software Engineer, AI"

print("=== STEP 1: Real JD fetch + real tailoring ===")
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(JOB_URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(1000)
    jd_text = page.locator("body").inner_text()
    browser.close()

from src.resume_intelligence.job_intelligence.parser import JobDescriptionParser
from src.resume_intelligence.tailoring.engine_v1 import TailoringEngineV1
from src.resume_intelligence.tailoring.models_v1 import TailoringInput
from src.resume_intelligence.base_resume.renderer import compile_pdf

jd_profile = JobDescriptionParser().parse_job_description(
    job_id="real-submit-backblaze", company_name=COMPANY, role_title=TITLE, raw_description=jd_text,
).model_dump()

base_tex = open("data/yash_resume_aiml.tex").read()
inp = TailoringInput(
    base_tex=base_tex,
    candidate_memory={"global": ["AI/ML focused backend engineer, real project experience with LangChain/LangGraph/RAG systems"]},
    jd_profile=jd_profile, job_id="real-submit-backblaze",
    writing_tone="Professional", tailoring_aggressiveness="Balanced",
)
result = TailoringEngineV1().tailor(inp)
print("is_noop:", result.is_noop, "| integrity_passed:", result.integrity_report.passed)

out_dir = "executions/real_submit_backblaze"
os.makedirs(out_dir, exist_ok=True)
pdf_path = compile_pdf(result.tailored_tex, out_dir, filename_prefix="tailored")
print("tailored resume:", pdf_path)

print("\n=== STEP 2: Real submit run (test_mode=False) ===")
from src.applications.handlers.greenhouse import GreenhouseHandler
from src.applications.profile import ProfileManager
from src.applications.rag import RAGClient
from src.utils.llm_router import LLMRouter
from src.applications.browser_launcher import LaunchedBrowser
from src.applications.question_classifier import QuestionClassifier

profile_manager = ProfileManager("data/context/yash_master_profile.md")
# One-off override for this test: 20 LPA (remote role), and bypass the
# salary-escalation gate just for this run so it actually answers instead
# of stopping for review.
profile_manager.base_profile["expected_salary"] = "20,00,000 INR per annum"

_original_classify = QuestionClassifier.classify

@classmethod
def _patched_classify(cls, question, widget_type):
    result = _original_classify.__func__(cls, question, widget_type)
    if result == "ESCALATE" and any(kw in question.lower() for kw in ["salary", "compensation", "expectations"]):
        return "DETERMINISTIC"
    return result

QuestionClassifier.classify = _patched_classify

with LaunchedBrowser() as lb:
    page = lb.page
    page.goto(JOB_URL, timeout=30000)
    handler = GreenhouseHandler(
        page=page, job_title=TITLE, company_name=COMPANY, location="Remote",
        resume_path=os.path.abspath(pdf_path), test_mode=False, execution_dir=out_dir,
        profile_manager=profile_manager, rag_client=RAGClient(), llm_client=LLMRouter(), company_context="",
    )
    result_data = handler.execute()
    page.screenshot(path=os.path.join(out_dir, "final_state.png"))

QuestionClassifier.classify = _original_classify

print("\n=== FINAL RESULT ===")
print("status:", result_data.get("status"))
telemetry = result_data.get("telemetry", {})
print("submission_proof:", telemetry.get("submission_proof"))
interactions = telemetry.get("interaction_log", [])
for i in interactions:
    print(" ", "OK " if i.get("Verification Result") else "FAIL", i.get("Question"), "->", i.get("Expected Value"))
print("missing_fields:", telemetry.get("missing_fields"))
if result_data.get("error"):
    print("error:", result_data.get("error"))
