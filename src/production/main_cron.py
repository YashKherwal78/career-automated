import os
import sys
import argparse
import subprocess
import time
from datetime import datetime

# Ensure absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.system.logger import setup_logger
from src.system.health_check import run_health_check
from src.system.integration_registry import print_registry
from src.crm.db_init import init_db

logger = setup_logger("MainCron")

class ProductionCron:
    def __init__(self, skip_health_check=False):
        os.makedirs("data/reports", exist_ok=True)
        self.summary_path = "data/reports/daily_summary.md"
        self.skip_health_check = skip_health_check
        
    def run(self):
        logger.info("========== STARTING CAREER AUTOMATED BOOT SEQUENCE ==========")
        logger.info("[1/8] Loading Configuration...")
        logger.info("[2/8] Initializing Logger...")
        
        logger.info("[3/8] Running System Health Check...")
        if not self.skip_health_check:
            run_health_check()
        else:
            logger.info("Health Check skipped via flag.")
        
        logger.info("[4/8] Loading Integration Registry...")
        print_registry()
        
        logger.info("[5/8] Validating Database Schema & Migrations...")
        init_db()
        
        logger.info("[6/8] Loading Candidate Context...")
        
        logger.info("[7/8] Initializing Pipeline Services...")
        
        logger.info("[8/8] Scheduler / Pipeline Ready. Entering Cron Loop.")
        logger.info("--- STARTING CAREER AUTOMATED PRODUCTION LOOP ---")
        
        stages = [
            ("Discovery Worker", "src/production/discovery_worker.py"),
            ("Match Engine Worker", "src/production/match_worker.py"),
            ("Application Worker", "src/production/application_worker.py"),
            ("Outreach Worker", "src/production/outreach_worker.py")
        ]
        
        results = []
        metrics = {}
        
        for name, script in stages:
            logger.info(f">> Executing Stage: {name} <<")
            
            # Using subprocess to isolate memory and enforce strict boundaries
            env = os.environ.copy()
            env["PYTHONPATH"] = "."
            
            
            start_time = time.time()
            result = subprocess.run(
                ["python3", script],
                capture_output=True,
                text=True,
                env=env
            )
            elapsed = time.time() - start_time
            metrics[name] = elapsed
            
            logger.info(result.stdout)
            if result.stderr:
                logger.error(f"[{name} STDERR]: {result.stderr}")
                
            success = result.returncode == 0
            results.append((name, success))
            
            if not success:
                logger.critical(f"CRITICAL FAILURE in {name}. Aborting remainder of pipeline.")
                break
                
        self._generate_summary(results, metrics)
        logger.info("--- PRODUCTION LOOP COMPLETE ---")
        
    def _generate_summary(self, results, metrics):
        lines = [
            "# CareerAutomated Daily Summary",
            f"**Execution Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## Pipeline Health"
        ]
        
        all_passed = True
        for name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            lines.append(f"- **{name}**: {status}")
            if not success:
                all_passed = False
                
        if all_passed:
            lines.insert(2, "> [!TIP]\n> **STATUS**: HEALTHY. All subsystems executed successfully.\n")
        else:
            lines.insert(2, "> [!CAUTION]\n> **STATUS**: CRITICAL FAILURE. Pipeline aborted.\n")
            
        lines.append("\n## Performance Metrics")
        lines.append("```text")
        for name, elapsed in metrics.items():
            lines.append(f"{name}\n{elapsed:.1f}s")
        lines.append("```")
            
        with open(self.summary_path, "w") as f:
            f.write("\n".join(lines))
            
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-health-check", action="store_true", help="Skip the system health check")
    args = parser.parse_args()
    
    cron = ProductionCron(skip_health_check=args.skip_health_check)
    cron.run()
