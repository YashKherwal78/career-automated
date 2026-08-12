from src.system.logger import setup_logger
logger = setup_logger('workday_adapter')
import os
from typing import Dict, Any

from src.applications.adapters.base_adapter import BaseAdapter, ApplicationResult, derive_diagnosis
from src.applications.browser_launcher import LaunchedBrowser
from src.applications.handlers.workday import WorkdayHandler

class WorkdayAdapter(BaseAdapter):
    def __init__(self, profile_manager=None, rag_client=None, llm_router=None):
        self.profile_manager = profile_manager
        self.rag_client = rag_client
        self.llm_router = llm_router

    def apply(self, job: Dict[str, Any], resume_path: str, profile_manager: Any, test_mode: bool = False, user_id: str = None) -> ApplicationResult:
        logger.info(f"[WorkdayAdapter] Launching browser for Job: {job.get('id')} - {job.get('company_name')}")

        execution_dir = f"executions/job_{job.get('id')}"
        os.makedirs(execution_dir, exist_ok=True)

        with LaunchedBrowser() as lb:
            page = lb.page
            try:
                page.goto(job.get("apply_url") or job.get("job_url"), timeout=30000)

                handler = WorkdayHandler(
                    page=page,
                    job_title=job.get("job_title", ""),
                    company_name=job.get("company_name", ""),
                    location=job.get("location", ""),
                    resume_path=resume_path,
                    test_mode=test_mode,
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

                telemetry = result_data.get("telemetry", {})
                really_submitted = telemetry.get("really_submitted", False)

                return ApplicationResult(
                    status=status,
                    confirmation_url=page.url if really_submitted else "",
                    screenshot_path=screenshot_path,
                    submitted_answers={},
                    failure_reason=derive_diagnosis(telemetry) if status != "COMPLETED" else "",
                    really_submitted=really_submitted,
                )

            except Exception as e:
                logger.info(f"[WorkdayAdapter] Exception: {e}")
                screenshot_path = os.path.join(execution_dir, "error_state.png")
                try:
                    page.screenshot(path=screenshot_path)
                except Exception:
                    pass

                return ApplicationResult(
                    status="FAILED",
                    confirmation_url="",
                    screenshot_path=screenshot_path,
                    submitted_answers={},
                    failure_reason=str(e)
                )
