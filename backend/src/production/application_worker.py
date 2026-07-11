import os
import sys
import time
from datetime import datetime

# Ensure absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.system.logger import setup_logger
from src.applications.handlers.wellfound import WellfoundHandler
from src.applications.feedback_tracker import FeedbackTracker
from src.crm.database import get_jobs_by_stage, update_job_state, log_heartbeat
from src.config.config import Config
from src.system.state import WorkflowState
from src.crm.state_machine import PipelineStage

logger = setup_logger("ApplicationWorker")

class ApplicationWorker:
    def __init__(self):
        self.tracker = FeedbackTracker()
        self.limit = getattr(Config, "WELLFOUND_DAILY_LIMIT", 3)
        
    def run(self):
        start_time = time.time()
        start_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"[{start_str}] ApplicationWorker: Starting (Limit: {self.limit})...")
        
        # Pull MATCHED jobs
        jobs = get_jobs_by_stage("MATCHED")
        if not jobs:
            logger.info("ApplicationWorker: No MATCHED jobs in queue.")
            self._write_report(0, 0, 0, [])
            end_time = time.time()
            log_heartbeat("Application Worker", WorkflowState.COMPLETED.name, start_str, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), end_time - start_time, 0)
            return
            
        # Sort by highest score
        jobs.sort(key=lambda x: x["opportunity_score"], reverse=True)
        selected_jobs = jobs[:self.limit]
        
        logger.info(f"ApplicationWorker: Processing Top {len(selected_jobs)} jobs.")
        
        applied_count = 0
        review_count = 0
        failed_count = 0
        
        results = []
        
        for job in selected_jobs:
            logger.info(f"--- Applying: {job['role']} @ {job['company']} (Score: {job['opportunity_score']}) ---")
            try:
                # 1. Tailor Resume via Agent 5
                base_resume = "yash_resume_base_v2.tex"
                from src.resume.agent5_resume_tailor import tailor_resume
                from src.utils.llm_router import LLMRouter
                llm = LLMRouter()
                resume_path, selected_project = tailor_resume(llm, base_resume, job["company"], job["role"], job["description"] or "", job["id"], "data/resumes", mode="application")
                
                # 2. Dispatch to ATS
                state_name = "FAILED"
                if "greenhouse.io" in job["url"]:
                    from src.applications.handlers.greenhouse import GreenhouseHandler
                    from playwright.sync_api import sync_playwright
                    with sync_playwright() as p:
                        browser = p.chromium.launch(headless=True)
                        page = browser.new_page()
                        page.goto(job["url"])
                        handler = GreenhouseHandler(page, job["role"], job["company"], "", resume_path)
                        state_dict = handler.execute()
                        state_name = state_dict.get("status", "FAILED")
                        browser.close()
                else:
                    handler = WellfoundHandler(job["url"])
                    state_obj = handler.execute()
                    state_name = state_obj.name
                    
                class DummyState:
                    def __init__(self, name):
                        self.name = name
                state = DummyState(state_name)
                
                if state.name == "COMPLETED":
                    new_stage = "APPLIED"
                    applied_count += 1
                elif state.name == "REVIEW_REQUIRED":
                    new_stage = "MANUAL_REVIEW"
                    review_count += 1
                elif state.name == "NOT_IMPLEMENTED":
                    new_stage = "NOT_IMPLEMENTED"
                    failed_count += 1
                elif state.name == "OTP_REQUIRED" or state.name == "CAPTCHA_REQUIRED":
                    new_stage = "MANUAL_REVIEW"
                    review_count += 1
                else:
                    new_stage = "FAILED"
                    failed_count += 1
                    
                update_job_state(job["id"], new_stage, state.name)
                
                # Feedback loop
                self.tracker.log_outcome(
                    company=job["company"],
                    role=job["role"],
                    score=job["opportunity_score"],
                    why=job["why_this_job"],
                    resume_ver="Agent 5",
                    projects=["CareerAutomated", "YAAR"], # Reordered projects
                    answers={},
                    outcome=state.name
                )
                
                results.append({"job": job, "status": new_status, "error": None})
                
            except Exception as e:
                logger.error(f"Application Error: {e}")
                update_job_state(job["id"], "FAILED", WorkflowState.FAILED.name, {"rejection_reason": str(e)})
                failed_count += 1
                results.append({"job": job, "status": "FAILED", "error": str(e)})
                
            time.sleep(2)
            
        logger.info(f"ApplicationWorker: Done. APPLIED: {applied_count}, MANUAL_REVIEW: {review_count}, FAILED/NOT_IMPL: {failed_count}")
        self._write_report(len(selected_jobs), applied_count, review_count, results)
        
        end_time = time.time()
        log_heartbeat("Application Worker", WorkflowState.COMPLETED.name, start_str, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), end_time - start_time, applied_count + review_count)
        
    def _write_report(self, attempted, applied, review, results):
        report_path = "data/reports/application_report.md"
        lines = [
            "# Application Report",
            f"**Run Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## Metrics",
            f"- **Applications Attempted**: {attempted}",
            f"- **Successfully Applied**: {applied}",
            f"- **Routed to Manual Review**: {review}",
            f"- **Failures**: {attempted - applied - review}",
            "\n## Job Statuses"
        ]
        
        for r in results:
            job = r["job"]
            status = r["status"]
            err = f" (Error: {r['error']})" if r["error"] else ""
            lines.append(f"- **[{status}]** {job['role']} @ {job['company']}{err}")
            
        if not results:
            lines.append("- No applications processed.")
            
        with open(report_path, "w") as f:
            f.write("\n".join(lines))

if __name__ == "__main__":
    worker = ApplicationWorker()
    worker.run()
