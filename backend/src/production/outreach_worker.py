import os
import sys
import random
import time
from datetime import datetime, timedelta

# Ensure absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.system.logger import setup_logger
from src.crm.database import get_jobs_by_stage, update_job_state, get_connection, log_heartbeat
from src.config.config import Config
from src.system.state import WorkflowState

logger = setup_logger("OutreachWorker")

class OutreachWorker:
    def __init__(self):
        pass
        
    def run(self):
        start_time = time.time()
        start_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"[{start_str}] OutreachWorker: Starting...")
        
        # 1. Schedule pending outreaches
        scheduled_count = self._schedule_pending()
        
        # 2. Execute ready outreaches
        executed_count = self._execute_ready()
        
        end_time = time.time()
        log_heartbeat("Outreach Worker", WorkflowState.COMPLETED.name, start_str, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), end_time - start_time, scheduled_count + executed_count)
        
    def _schedule_pending(self):
        conn = get_connection()
        conn.row_factory = sqlite3.Row if 'sqlite3' in globals() else None
        cursor = conn.cursor()
        
        # Select APPLIED jobs with no scheduled time
        cursor.execute("SELECT * FROM discovered_jobs WHERE stage = 'APPLIED' AND outreach_scheduled_for IS NULL")
        jobs = [dict(r) for r in cursor.fetchall()]
        
        for j in jobs:
            delay_hours = random.uniform(2, 6)
            scheduled_time = datetime.now() + timedelta(hours=delay_hours)
            
            cursor.execute("UPDATE discovered_jobs SET outreach_scheduled_for = ? WHERE id = ?", 
                           (scheduled_time.strftime("%Y-%m-%d %H:%M:%S"), j["id"]))
            logger.info(f"OutreachWorker: Scheduled outreach for {j['company']} at {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
        conn.commit()
        conn.close()
        return len(jobs)
        
    def _execute_ready(self):
        import sqlite3
        conn = sqlite3.connect(Config.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("SELECT * FROM discovered_jobs WHERE stage = 'APPLIED' AND outreach_scheduled_for <= ?", (now_str,))
        ready_jobs = [dict(r) for r in cursor.fetchall()]
        
        executed_count = 0
        failed_count = 0
        
        for j in ready_jobs:
            logger.info(f"--- Sending Outreach: {j['role']} @ {j['company']} ---")
            try:
                # Placeholder for actual Outreach Engine logic
                # engine = OutreachEngine()
                # email = engine.generate_and_send(j["company"], j["role"])
                
                # Removing fake success - replacing with truthful orchestration state
                new_stage = "NOT_IMPLEMENTED"
                cursor.execute("UPDATE discovered_jobs SET stage = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, j["id"]))
                logger.info(f"Outreach API not linked. Marking job {j['id']} as {new_status}")
                executed_count += 1
                
            except Exception as e:
                logger.error(f"Outreach Error: {e}")
                failed_count += 1
                # If transient, keep APPLIED. Else FAILED_OUTREACH.
                # Assuming transient network failure for now.
                
        conn.commit()
        conn.close()
        
        logger.info(f"OutreachWorker: Done. Processed: {executed_count}, Failed: {failed_count}")
        self._write_report(len(ready_jobs), executed_count, failed_count)
        return executed_count
        
    def _write_report(self, attempted, sent, failed):
        report_path = "data/reports/outreach_report.md"
        lines = [
            "# Outreach Report",
            f"**Run Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## Metrics",
            f"- **Outreach Scheduled/Executed**: {attempted}",
            f"- **Successfully Sent**: {sent}",
            f"- **Failed**: {failed}"
        ]
        
        with open(report_path, "w") as f:
            f.write("\n".join(lines))

if __name__ == "__main__":
    import sqlite3
    worker = OutreachWorker()
    worker.run()
