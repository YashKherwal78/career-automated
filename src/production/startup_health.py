import os
import sqlite3
import time
from datetime import datetime
from src.config.config import Config
from src.crm.database import log_heartbeat

class HealthMonitor:
    def __init__(self):
        self.report_path = os.path.join(Config.DATA_DIR, "..", "startup_health_report.md")
        
    def check_all(self):
        start_time = time.time()
        start_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        errors = []
        
        # 1. Database Check
        try:
            conn = sqlite3.connect(Config.DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cursor.fetchall()]
            if "discovered_jobs" not in tables:
                errors.append("Missing table: discovered_jobs in CRM DB.")
            conn.close()
        except Exception as e:
            errors.append(f"Database error: {e}")
            
        # 2. Agent 5 Resume Compiler Check
        if os.system("pdflatex -version > /dev/null 2>&1") != 0:
            errors.append("pdflatex not installed or not in PATH.")
            
        # 3. Candidate DB
        if not os.path.exists(os.path.join(Config.DATA_DIR, "context", "master_candidate_profile.json")):
            errors.append("master_candidate_profile.json is missing.")
            
        # 4. Apify Keys
        if not Config.APIFY_KEYS and not os.getenv("APIFY_API_KEY"):
            errors.append("Missing APIFY_API_KEY")
            
        # Generate Report
        lines = [
            "# Startup Health Report",
            "**Status**: " + ("❌ FAILED" if errors else "✅ PASSING"),
            "**Date**: " + os.popen("date").read().strip(),
            "\n## Critical Failures"
        ]
        
        if errors:
            for err in errors:
                lines.append(f"- {err}")
        else:
            lines.append("- None. All systems operational.")
            
        with open(self.report_path, "w") as f:
            f.write("\n".join(lines))
            
        end_time = time.time()
        end_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if errors:
            log_heartbeat("Startup Health", "FAILED", start_str, end_str, end_time - start_time, 0, "; ".join(errors))
            print("CRITICAL: Startup Health Check Failed. Aborting execution.")
            exit(1)
        else:
            log_heartbeat("Startup Health", "SUCCESS", start_str, end_str, end_time - start_time, 1)
            
if __name__ == "__main__":
    monitor = HealthMonitor()
    monitor.check_all()
    print("Health check passed.")
