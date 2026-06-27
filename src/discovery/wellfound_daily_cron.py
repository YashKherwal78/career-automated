import os
import time
from datetime import datetime
from src.discovery.wellfound_scraper import WellfoundScraper
from src.applications.match_engine import MatchEngine
from src.applications.handlers.wellfound import WellfoundHandler
from src.applications.feedback_tracker import FeedbackTracker
from src.config.config import Config

class WellfoundDailyCron:
    def __init__(self):
        self.scraper = WellfoundScraper()
        self.engine = MatchEngine()
        self.tracker = FeedbackTracker()
        self.limit = getattr(Config, "WELLFOUND_DAILY_LIMIT", 3)
        
    def run(self):
        print(f"[{datetime.now()}] Starting Wellfound Daily Cron (Limit: {self.limit})")
        
        # 1. Discover
        target_roles = ["AI Product Manager", "Associate Product Manager", "Founder's Office"]
        target_locations = ["Remote", "Bangalore", "Gurgaon", "Mumbai"]
        
        jobs = self.scraper.discover_jobs(target_roles, target_locations, max_items=50)
        if not jobs:
            print("No jobs discovered. Exiting.")
            return
            
        # 2. Score
        print("Scoring jobs...")
        scored_jobs = []
        for j in jobs:
            score_res = self.engine.evaluate(j["title"], j["company"], j["location"], j["description"], j["employees"])
            j.update(score_res)
            scored_jobs.append(j)
            
        # Normalize scores to V1.4 strict distribution
        scored_jobs = self.engine.normalize_batch(scored_jobs)
        
        # 3. Filter top jobs
        top_jobs = [j for j in scored_jobs if j["passed"]]
        top_jobs.sort(key=lambda x: x["opportunity_score"], reverse=True)
        
        selected_jobs = top_jobs[:self.limit]
        print(f"Selected Top {len(selected_jobs)} jobs for application out of {len(top_jobs)} passing jobs.")
        
        # 4. Apply
        for rank, job in enumerate(selected_jobs, 1):
            print(f"\n--- Executing Job {rank}/{self.limit}: {job['title']} @ {job['company']} ---")
            print(f"Opportunity Score: {job['opportunity_score']}")
            
            # Execute Application Flow
            handler = WellfoundHandler(job["url"])
            state = handler.execute()
            
            print(f"Final State: {state.name}")
            
            # 5. Feedback Loop Logging
            outcome = "INTERVIEW" if state.name == "SUBMITTED" else "REJECTED"
            # We map SUBMITTED to INTERVIEW tracking to track funnel, or we just track as SUBMITTED until human updates it.
            # As per prompt: "For every job eventually marked as INTERVIEW Store ... For every job marked REJECTED Store..."
            # For now, we seed the database with the application state.
            
            self.tracker.log_outcome(
                company=job["company"],
                role=job["title"],
                score=job["opportunity_score"],
                why=job["why_this_job"],
                resume_ver="Agent 5", # V1.2 Rule
                projects=["CareerAutomated", "YAAR"], # Mocked Agent 5 ordering
                answers={},
                outcome=state.name # SUBMITTED or MANUAL_REVIEW
            )
            
            time.sleep(2)
            
        # 6. Generate Daily Report
        report_path = os.path.join(Config.DATA_DIR, "..", "daily_wellfound_report.md")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "# Daily Wellfound Execution Report",
            f"\n**LAST_DISCOVERY_RUN**: {now_str}",
            f"**LAST_DISCOVERY_SUCCESS**: {now_str if len(jobs) > 0 else 'FAILED'}",
            f"**JOBS_DISCOVERED**: {len(jobs)}",
            "\n## Application Summary",
            f"- Passing Jobs: {len(top_jobs)}",
            f"- Applications Attempted: {len(selected_jobs)}"
        ]
        
        if len(jobs) == 0:
            lines.append("\n> [!CAUTION]")
            lines.append("> **ALERT**: 0 jobs discovered. The Discovery Engine failed or returned empty.")
            
        with open(report_path, "w") as f:
            f.write("\n".join(lines))
            
        print(f"[{datetime.now()}] Wellfound Daily Cron Complete. Report saved to {report_path}")

if __name__ == "__main__":
    cron = WellfoundDailyCron()
    cron.run()
