import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from playwright.sync_api import sync_playwright
from src.resume_intelligence.job_intelligence.parser import JobDescriptionParser
from src.resume_intelligence.tailoring.engine_v1 import TailoringEngineV1
from src.resume_intelligence.tailoring.models_v1 import TailoringInput
from src.resume_intelligence.base_resume.renderer import compile_pdf
from src.applications.handlers.ashby import AshbyHandler
from src.applications.profile import ProfileManager
from src.applications.rag import RAGClient
from src.utils.llm_router import LLMRouter
from src.applications.browser_launcher import LaunchedBrowser

job = {"url": "https://jobs.ashbyhq.com/ema/eb62df31-0370-447f-8cc6-707e79cbc9fa",
       "company": "Ema", "title": "Software Engineer, Backend - India"}
execution_dir = "executions/classifier_fix_verify"
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
    job_id="classifier-fix-verify", company_name=job["company"], role_title=job["title"], raw_description=jd_text,
).model_dump()
tailor_inp = TailoringInput(
    base_tex=base_tex, candidate_memory={"global": ["AI/ML focused backend engineer"]},
    jd_profile=jd_profile, job_id="classifier-fix-verify",
    writing_tone="Professional", tailoring_aggressiveness="Balanced",
)
tailor_result = TailoringEngineV1().tailor(tailor_inp)
pdf_path = compile_pdf(tailor_result.tailored_tex, execution_dir, filename_prefix="tailored") or "data/Resume_aiml.pdf"

with LaunchedBrowser() as lb:
    page = lb.page
    page.goto(job["url"], timeout=30000)
    handler = AshbyHandler(
        page=page, job_title=job["title"], company_name=job["company"], location="India",
        resume_path=os.path.abspath(pdf_path), test_mode=True, execution_dir=execution_dir,
        profile_manager=profile_manager, rag_client=rag_client, llm_client=llm_router, company_context="",
    )
    result_data = handler.execute()

telemetry = result_data.get("telemetry", {})
print(f"\nRESULT: {result_data.get('status')}")
if telemetry.get("missing_fields"):
    print("missing:", telemetry["missing_fields"])
for entry in telemetry.get("interaction_log", []):
    if entry.get("Verification Result") is not True:
        print("FAILED:", entry)
