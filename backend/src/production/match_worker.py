import os
import sys
import time
from datetime import datetime

# Ensure absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.system.logger import setup_logger
from src.jobs.quality_filter import apply_hard_reject_rules
from src.crm.database import get_jobs_by_stage, update_job_state, log_heartbeat
from src.config.config import Config
from src.system.state import WorkflowState
from src.crm.state_machine import PipelineStage

logger = setup_logger("MatchWorker")

class MatchWorker:
    def __init__(self):
        self.engine = MatchEngine()
        
    def run(self):
        start_time = time.time()
        start_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"[{start_str}] MatchWorker: Starting...")
        
        # Pull all jobs sitting in DISCOVERED queue
        jobs = get_jobs_by_stage("DISCOVERED")
        
        if not jobs:
            logger.info("MatchWorker: No DISCOVERED jobs in queue.")
            self._write_report(0, 0, 0, [])
            end_time = time.time()
            log_heartbeat("Match Worker", WorkflowState.COMPLETED.name, start_str, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), end_time - start_time, 0)
            return
            
        logger.info(f"MatchWorker: Processing {len(jobs)} jobs...")
        
        scored_jobs = []
        for j in jobs:
            # Reconstruct the dict structure expected by MatchEngine
            score_res = self.engine.evaluate(
                j["role"], 
                j["company"], 
                "Remote", # Assuming location is embedded in description or unknown
                j["description"] or "", 
                j["employee_count"] or ""
            )
            j.update(score_res)
            # Map back to 'raw_score' for normalization logic
            j["raw_score"] = score_res["opportunity_score"]
            scored_jobs.append(j)
            
        # Normalize batch
        scored_jobs = self.engine.normalize_batch(scored_jobs)
        
        passed_count = 0
        rejected_count = 0
        
        for j in scored_jobs:
            try:
                new_status = "MATCHED" if j["passed"] else "REJECTED"
                update_job_state(
                    j["id"], 
                    new_status,
                    WorkflowState.COMPLETED.name,
                    {
                        "opportunity_score": j["opportunity_score"],
                        "why_this_job": j["why_this_job"],
                        "rejection_reason": j["rejection_reason"]
                    }
                )
                
                if j["passed"]:
                    passed_count += 1
                else:
                    rejected_count += 1
            except Exception as e:
                logger.error(f"Match Error: {e}")
                update_job_state(j["id"], "REJECTED", WorkflowState.FAILED.name, {"rejection_reason": f"Match Error: {e}"})
                rejected_count += 1
                
        logger.info(f"MatchWorker: Finished. {passed_count} MATCHED, {rejected_count} REJECTED.")
        self._write_report(len(jobs), passed_count, rejected_count, scored_jobs)
        
        end_time = time.time()
        log_heartbeat("Match Worker", WorkflowState.COMPLETED.name, start_str, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), end_time - start_time, len(jobs))
        
    def _write_report(self, total, passed, rejected, scored_jobs):
        report_path = "data/reports/match_report.md"
        
        # Get top 5 matched
        matched_jobs = [j for j in scored_jobs if j["passed"]]
        matched_jobs.sort(key=lambda x: x["opportunity_score"], reverse=True)
        top_5 = matched_jobs[:5]
        
        lines = [
            "# Match Engine Report",
            f"**Run Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## Metrics",
            f"- **Jobs Processed**: {total}",
            f"- **Jobs Passed (MATCHED)**: {passed}",
            f"- **Jobs Failed (REJECTED)**: {rejected}",
            "\n## Top Matched Candidates"
        ]
        
        for j in top_5:
            lines.append(f"- **[{j['opportunity_score']}]** {j['role']} @ {j['company']} (URL: {j['url']})")
            
        if not top_5:
            lines.append("- No matched candidates in this run.")
            
        with open(report_path, "w") as f:
            f.write("\n".join(lines))
            
if __name__ == "__main__":
    worker = MatchWorker()
    worker.run()
