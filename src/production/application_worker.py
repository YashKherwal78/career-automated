import os
import time
from datetime import datetime
from src.applications.handlers.wellfound import WellfoundHandler
from src.applications.feedback_tracker import FeedbackTracker
from src.crm.database import get_jobs_by_status, update_job_status, log_heartbeat
from src.config.config import Config

class ApplicationWorker:
    def __init__(self):
        self.tracker = FeedbackTracker()
        self.limit = getattr(Config, "WELLFOUND_DAILY_LIMIT", 3)
        
    def run(self):
        start_time = time.time()
        start_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{start_str}] ApplicationWorker: Starting (Limit: {self.limit})...")
        
        # Pull MATCHED jobs
        jobs = get_jobs_by_status("MATCHED")
        if not jobs:
            print("ApplicationWorker: No MATCHED jobs in queue.")
            self._write_report(0, 0, 0, [])
            end_time = time.time()
            log_heartbeat("Application Worker", "SUCCESS", start_str, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), end_time - start_time, 0)
            return
            
        # Sort by highest score
        jobs.sort(key=lambda x: x["opportunity_score"], reverse=True)
        selected_jobs = jobs[:self.limit]
        
        print(f"ApplicationWorker: Processing Top {len(selected_jobs)} jobs.")
        
        applied_count = 0
        review_count = 0
        failed_count = 0
        
        results = []
        
        for job in selected_jobs:
            print(f"--- Applying: {job['role']} @ {job['company']} (Score: {job['opportunity_score']}) ---")
            try:
                # Dispatch to native handler based on source (assuming Wellfound here)
                handler = WellfoundHandler(job["url"])
                state = handler.execute()
                
                if state.name == "SUBMITTED":
                    new_status = "APPLIED"
                    applied_count += 1
                elif state.name == "MANUAL_REVIEW":
                    new_status = "MANUAL_REVIEW"
                    review_count += 1
                else:
                    new_status = "FAILED"
                    failed_count += 1
                    
                update_job_status(job["id"], new_status)
                
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
                print(f"Application Error: {e}")
                update_job_status(job["id"], "FAILED", {"rejection_reason": str(e)})
                failed_count += 1
                results.append({"job": job, "status": "FAILED", "error": str(e)})
                
            time.sleep(2)
            
        print(f"ApplicationWorker: Done. APPLIED: {applied_count}, MANUAL_REVIEW: {review_count}, FAILED: {failed_count}")
        self._write_report(len(selected_jobs), applied_count, review_count, results)
        
        end_time = time.time()
        log_heartbeat("Application Worker", "SUCCESS", start_str, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), end_time - start_time, applied_count + review_count)
        
    def _write_report(self, attempted, applied, review, results):
        report_path = os.path.join(Config.DATA_DIR, "..", "application_report.md")
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
