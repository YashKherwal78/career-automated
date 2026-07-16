from src.api.db import get_connection
from src.system.logger import setup_logger
logger = setup_logger('google_jobs_provider')
import yaml
from typing import List, Optional
from datetime import datetime
from src.discovery.providers.base_provider import StandardJob
from src.integrations.apify_manager import ApifyManager

class GoogleJobsProvider:
    def __init__(self):
        self._pipeline_type = 'PIPELINE_B'
        self.manager = ApifyManager()
        self.actor_id = "jupri/google-jobs-scraper"
        
    def _load_preferences(self) -> dict:
        try:
            with open("src/config/user_preferences.yaml", "r") as f:
                return yaml.safe_load(f)
        except Exception:
            return {
                "target_roles": ["Product Manager", "Software Engineer"],
                "locations": ["India"]
            }

    ROLE_LABELS = {
        "associate_product_manager": "Associate Product Manager",
        "product_manager": "Product Manager",
        "product_analyst": "Product Analyst",
        "founders_office": "Founder's Office",
        "chief_of_staff": "Chief of Staff",
        "ai_engineer": "AI Engineer",
        "machine_learning_engineer": "Machine Learning Engineer",
        "software_engineer": "Software Engineer",
        "data_scientist": "Data Scientist",
    }

    def _discover_jobs_internal(self, last_sync_timestamp: Optional[str]) -> List[StandardJob]:
        prefs = self._load_preferences()
        roles = prefs.get("target_roles", ["Software Engineer"])
        locations = prefs.get("locations", ["India"])

        # Build targeted queries: "entry level Associate Product Manager jobs in India past week"
        queries = []
        for role in roles:
            label = self.ROLE_LABELS.get(role, role.replace("_", " ").title())
            for loc in locations:
                queries.append(f"entry level {label} jobs in {loc} posted this week")

        # Rotate through queries 3 at a time to conserve credits
        MAX_QUERIES_PER_RUN = 3
        start_idx = 0
        if last_sync_timestamp and last_sync_timestamp.isdigit():
            start_idx = int(last_sync_timestamp) % len(queries)
        queries_this_run = (queries[start_idx:] + queries[:start_idx])[:MAX_QUERIES_PER_RUN]
        next_cursor = str((start_idx + MAX_QUERIES_PER_RUN) % len(queries))

        client, key_id = self.manager.get_client(tier=4, category="google_jobs_pipeline_b")
        if not client:
            raise Exception("No Apify client available for Google jobs")

        logger.info(f"GoogleJobsProvider: Searching {len(queries_this_run)} targeted queries: {queries_this_run}")

        run_input = {
            "queries": "\n".join(queries_this_run),
            "maxConcurrency": 3,
            "maxPagesPerQuery": 1
        }
        
        try:
            run = client.actor(self.actor_id).call(run_input=run_input)
        except Exception as e:
            err_str = str(e)
            if "Monthly usage hard limit exceeded" in err_str or "monthly" in err_str.lower():
                logger.warning(f"GoogleJobsProvider: Key {key_id} hit monthly limit — marking as RATE_LIMITED")
                import sqlite3
                from src.config.config import Config
                try:
                    conn = get_connection()
                    conn.execute("UPDATE apify_keys SET status = 'RATE_LIMITED' WHERE id = ?", (key_id,))
                    conn.commit()
                    conn.close()
                except Exception:
                    pass
            raise

        dataset_id = getattr(run, "default_dataset_id", None) or getattr(run, "defaultDatasetId", None)
            
        if not dataset_id:
            self.manager.record_usage(key_id, "google_jobs_pipeline_b", credits=0, useful_results=0, success=False)
            raise Exception("Apify Run did not return a dataset ID")
            
        jobs = []
        for item in client.dataset(dataset_id).iterate_items():
            title = item.get("title", "Unknown")
            company = item.get("companyName", "Unknown")
            url = item.get("applyLink", item.get("googleJobsUrl", ""))
            
            exclude_keywords = prefs.get("exclude_keywords", ["senior", "lead", "director", "manager"])
            if any(exc.lower() in title.lower() for exc in exclude_keywords if exc.strip()):
                continue
                
            jobs.append(StandardJob(
                company=company,
                role=title,
                location=item.get("location", "Unknown"),
                remote_hybrid_onsite="Unknown",
                experience_required="",
                skills=[],
                job_description=item.get("description", ""),
                ats_type="google_jobs",
                application_url=url,
                source="google_jobs",
                date_posted=item.get("postedAt", datetime.now().isoformat())
            ))
            
        self.manager.record_usage(key_id, "google_jobs_pipeline_b", credits=0.025, useful_results=len(jobs), success=True)
        return jobs, next_cursor
