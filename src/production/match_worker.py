import os
import time
from datetime import datetime
from src.applications.match_engine import MatchEngine
from src.crm.database import get_jobs_by_status, update_job_status, log_heartbeat
from src.config.config import Config

class MatchWorker:
    def __init__(self):
        self.engine = MatchEngine()
        
    def run(self):
        start_time = time.time()
        start_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{start_str}] MatchWorker: Starting...")
        
        # Pull all jobs sitting in DISCOVERED queue
        jobs = get_jobs_by_status("DISCOVERED")
        
        if not jobs:
            print("MatchWorker: No DISCOVERED jobs in queue.")
            self._write_report(0, 0, 0, [])
            end_time = time.time()
            log_heartbeat("Match Worker", "SUCCESS", start_str, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), end_time - start_time, 0)
            return
            
        print(f"MatchWorker: Processing {len(jobs)} jobs...")
        
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
            new_status = "MATCHED" if j["passed"] else "REJECTED"
            update_job_status(
                j["id"], 
                new_status,
                extra_data={
                    "opportunity_score": j["opportunity_score"],
                    "why_this_job": j["why_this_job"],
                    "rejection_reason": j["rejection_reason"]
                }
            )
            
            if j["passed"]:
                passed_count += 1
            else:
                rejected_count += 1
                
        print(f"MatchWorker: Finished. {passed_count} MATCHED, {rejected_count} REJECTED.")
        self._write_report(len(jobs), passed_count, rejected_count, scored_jobs)
        
        end_time = time.time()
        log_heartbeat("Match Worker", "SUCCESS", start_str, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), end_time - start_time, len(jobs))
        
    def _write_report(self, total, passed, rejected, scored_jobs):
        report_path = os.path.join(Config.DATA_DIR, "..", "match_report.md")
        
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
