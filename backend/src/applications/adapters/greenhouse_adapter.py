from src.system.logger import setup_logger
logger = setup_logger('greenhouse_adapter')
import os
import json
from typing import Dict, Any
from playwright.sync_api import sync_playwright

from src.applications.adapters.base_adapter import BaseAdapter, ApplicationResult
from src.applications.handlers.greenhouse import GreenhouseHandler

class GreenhouseAdapter(BaseAdapter):
    def __init__(self, profile_manager=None, rag_client=None, llm_router=None):
        self.profile_manager = profile_manager
        self.rag_client = rag_client
        self.llm_router = llm_router

    def apply(self, job: Dict[str, Any], resume_path: str, profile_manager: Any) -> ApplicationResult:
        logger.info(f"[GreenhouseAdapter] Launching browser for Job: {job.get('id')} - {job.get('company_name')}")
        
        execution_dir = f"executions/job_{job.get('id')}"
        os.makedirs(execution_dir, exist_ok=True)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False) # Keep visible for debugging/testing
            context = browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            
            try:
                page.goto(job.get("apply_url") or job.get("job_url"), timeout=30000)
                
                handler = GreenhouseHandler(
                    page=page,
                    job_title=job.get("job_title", ""),
                    company_name=job.get("company_name", ""),
                    location=job.get("location", ""),
                    resume_path=resume_path,
                    test_mode=False,
                    execution_dir=execution_dir,
                    profile_manager=self.profile_manager,
                    rag_client=self.rag_client,
                    llm_client=self.llm_router,
                    company_context=""
                )
                
                result_data = handler.execute()
                status = result_data.get("status", "FAILED")
                
                screenshot_path = os.path.join(execution_dir, "final_state.png")
                page.screenshot(path=screenshot_path)
                
                # Extract answers
                telemetry = result_data.get("telemetry", {})
                interactions = telemetry.get("interaction_log", [])
                answers = {i.get("Question"): i.get("Expected Value") for i in interactions if i.get("Verification Result")}
                
                return ApplicationResult(
                    status=status,
                    confirmation_url=page.url if status == "SUBMITTED" else "",
                    screenshot_path=screenshot_path,
                    submitted_answers=answers,
                    failure_reason=telemetry.get("diagnosis_json", "") if status != "SUBMITTED" else ""
                )
                
            except Exception as e:
                logger.info(f"[GreenhouseAdapter] Exception: {e}")
                screenshot_path = os.path.join(execution_dir, "error_state.png")
                try:
                    page.screenshot(path=screenshot_path)
                except: pass
                
                return ApplicationResult(
                    status="FAILED",
                    confirmation_url="",
                    screenshot_path=screenshot_path,
                    submitted_answers={},
                    failure_reason=str(e)
                )
            finally:
                browser.close()
