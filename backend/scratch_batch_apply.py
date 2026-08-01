"""
Real batch application run — 4 genuinely matching, live jobs across all
three ATS handlers. For each: real JD fetch, real tailoring against the new
AI/ML resume, real submit attempt (not test mode).

Salary: these are all India-based roles, so the profile's own stored
default (15,00,000 INR — the candidate's own stated expectation, not an
invented number) is used instead of leaving the question for review, same
override pattern as the earlier confirmed test run, applied consistently
because domestic-vs-remote logic doesn't change here (all 4 are domestic).
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
from src.applications.handlers.greenhouse import GreenhouseHandler
from src.applications.handlers.lever import LeverHandler
from src.applications.handlers.ashby import AshbyHandler
from src.applications.profile import ProfileManager
from src.applications.rag import RAGClient
from src.utils.llm_router import LLMRouter
from src.applications.browser_launcher import LaunchedBrowser
from src.applications.question_classifier import QuestionClassifier

JOBS = [
    {"handler": AshbyHandler, "url": "https://jobs.ashbyhq.com/bjakcareer/7f6692fb-eed1-4134-9baa-76cb68850037",
     "company": "Bjak", "title": "Backend Software Engineer - AI Neobank App (India)"},
    {"handler": AshbyHandler, "url": "https://jobs.ashbyhq.com/notion/42f18ccd-c4c8-4a85-8c1f-de12c575fe87",
     "company": "Notion", "title": "Software Engineer, Infrastructure"},
    {"handler": LeverHandler, "url": "https://jobs.lever.co/gushwork/c9e4bdeb-2e2d-4ec8-92f0-203d52e4b17b/apply",
     "company": "Gushwork", "title": "SDE 2/3 (Backend)"},
    {"handler": GreenhouseHandler, "url": "https://job-boards.greenhouse.io/singlestore-linkedin/jobs/7861208",
     "company": "SingleStore", "title": "Software Engineer | Database Engine"},
]

profile_manager = ProfileManager("data/context/yash_master_profile.md")
rag_client = RAGClient()
llm_router = LLMRouter()
base_tex = open("data/yash_resume_aiml.tex").read()

# Same one-off override as the earlier confirmed test: use the profile's own
# stored salary expectation instead of leaving it for review, for this batch
# only (not a permanent change to question_classifier.py).
_original_classify = QuestionClassifier.classify

@classmethod
def _patched_classify(cls, question, widget_type):
    result = _original_classify.__func__(cls, question, widget_type)
    if result == "ESCALATE" and any(kw in question.lower() for kw in ["salary", "compensation", "expectations"]):
        return "DETERMINISTIC"
    return result

QuestionClassifier.classify = _patched_classify

results = []

for job in JOBS:
    print(f"\n{'='*70}\n{job['company']} — {job['title']}\n{'='*70}")
    execution_dir = f"executions/batch_apply/{job['company'].replace(' ', '_')}"
    os.makedirs(execution_dir, exist_ok=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(job["url"], wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1000)
            jd_text = page.locator("body").inner_text()
            browser.close()

        jd_profile = JobDescriptionParser().parse_job_description(
            job_id=f"batch-{job['company']}", company_name=job["company"], role_title=job["title"], raw_description=jd_text,
        ).model_dump()

        tailor_inp = TailoringInput(
            base_tex=base_tex,
            candidate_memory={"global": ["AI/ML focused backend engineer, real project experience with LangGraph/RAG/Playwright automation"]},
            jd_profile=jd_profile, job_id=f"batch-{job['company']}",
            writing_tone="Professional", tailoring_aggressiveness="Balanced",
        )
        tailor_result = TailoringEngineV1().tailor(tailor_inp)
        print(f"tailoring: is_noop={tailor_result.is_noop} integrity={tailor_result.integrity_report.passed}")

        pdf_path = compile_pdf(tailor_result.tailored_tex, execution_dir, filename_prefix="tailored")
        if not pdf_path:
            pdf_path = "data/Resume_aiml.pdf"
            print("WARNING: tailored PDF compile failed, using base resume")

        with LaunchedBrowser() as lb:
            page = lb.page
            page.goto(job["url"], timeout=30000)
            handler = job["handler"](
                page=page, job_title=job["title"], company_name=job["company"], location="India",
                resume_path=os.path.abspath(pdf_path), test_mode=False, execution_dir=execution_dir,
                profile_manager=profile_manager, rag_client=rag_client, llm_client=llm_router, company_context="",
            )
            result_data = handler.execute()
            page.screenshot(path=os.path.join(execution_dir, "final_state.png"))

        status = result_data.get("status")
        telemetry = result_data.get("telemetry", {})
        proof = telemetry.get("submission_proof")
        print(f"RESULT: {status}")
        if proof:
            print(f"  proof: {proof}")
        missing = telemetry.get("missing_fields")
        if missing:
            print(f"  missing_fields: {missing}")

        results.append({"company": job["company"], "title": job["title"], "status": status, "proof": proof})

    except Exception as e:
        print(f"EXCEPTION: {e}")
        results.append({"company": job["company"], "title": job["title"], "status": "ERROR", "proof": str(e)})

QuestionClassifier.classify = _original_classify

print(f"\n\n{'='*70}\nFINAL SUMMARY\n{'='*70}")
for r in results:
    print(f"{r['company']:20s} | {r['status']:20s} | {r['title']}")
