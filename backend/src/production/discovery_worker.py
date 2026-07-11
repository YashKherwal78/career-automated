import os
import time
from datetime import datetime
from src.discovery.wellfound_scraper import WellfoundScraper
from src.crm.database import insert_discovered_job, log_heartbeat
from src.config.config import Config

class DiscoveryWorker:
    def __init__(self):
        self.scraper = WellfoundScraper()
        
    def run(self):
        start_time = time.time()
        start_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{start_str}] DiscoveryWorker: Starting...")
        
        target_roles = ["AI Product Manager", "Associate Product Manager", "Founder's Office"]
        target_locations = ["Remote", "Bangalore", "Gurgaon", "Mumbai"]
        
        jobs = self.scraper.discover_jobs(target_roles, target_locations, max_items=50)
        
        inserted_count = 0
        duplicate_count = 0
        
        for job in jobs:
            # We insert with stage = DISCOVERED
            data = {
                "company": job["company"],
                "role": job["title"],
                "url": job["url"],
                "description": job["description"],
                "employee_count": job["employees"],
                "source": "Wellfound",
                "status": "DISCOVERED"
            }
            if insert_discovered_job(data):
                inserted_count += 1
            else:
                duplicate_count += 1
                
        print(f"DiscoveryWorker: Inserted {inserted_count} new jobs. Skipped {duplicate_count} duplicates.")
        
        report_path = os.path.join(Config.DATA_DIR, "..", "discovery_report.md")
        lines = [
            "# Discovery Report",
            f"**Run Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## Metrics",
            f"- **Jobs Found**: {len(jobs)}",
            f"- **New Jobs Inserted into CRM**: {inserted_count}",
            f"- **Duplicates Ignored**: {duplicate_count}"
        ]
        
        with open(report_path, "w") as f:
            f.write("\n".join(lines))
            
        end_time = time.time()
        end_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_heartbeat("Discovery Worker", WorkflowState.COMPLETED.name, start_str, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), end_time - start_time, inserted_count)
            
if __name__ == "__main__":
    worker = DiscoveryWorker()
    worker.run()
