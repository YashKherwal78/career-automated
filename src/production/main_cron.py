import os
import subprocess
from datetime import datetime
from src.config.config import Config

class ProductionCron:
    def __init__(self):
        self.summary_path = os.path.join(Config.DATA_DIR, "..", "daily_summary.md")
        
    def run(self):
        print(f"[{datetime.now()}] --- STARTING CAREER AUTOMATED PRODUCTION LOOP ---")
        
        stages = [
            ("Startup Health Check", "src/production/startup_health.py"),
            ("Discovery Worker", "src/production/discovery_worker.py"),
            ("Match Engine Worker", "src/production/match_worker.py"),
            ("Application Worker", "src/production/application_worker.py"),
            ("Outreach Worker", "src/production/outreach_worker.py")
        ]
        
        results = []
        
        for name, script in stages:
            print(f"\n>> Executing Stage: {name} <<")
            
            # Using subprocess to isolate memory and enforce strict boundaries
            env = os.environ.copy()
            env["PYTHONPATH"] = "."
            
            result = subprocess.run(
                ["python3", script],
                capture_output=True,
                text=True,
                env=env
            )
            
            print(result.stdout)
            if result.stderr:
                print(f"[{name} STDERR]:", result.stderr)
                
            success = result.returncode == 0
            results.append((name, success))
            
            if not success:
                print(f"CRITICAL FAILURE in {name}. Aborting remainder of pipeline.")
                break
                
        self._generate_summary(results)
        print(f"[{datetime.now()}] --- PRODUCTION LOOP COMPLETE ---")
        
    def _generate_summary(self, results):
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
            
        with open(self.summary_path, "w") as f:
            f.write("\n".join(lines))
            
if __name__ == "__main__":
    cron = ProductionCron()
    cron.run()
