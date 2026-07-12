from src.system.logger import setup_logger
logger = setup_logger('linkedin_jobs_provider')
import yaml
import urllib.parse
from typing import List, Optional
from datetime import datetime
from src.discovery.providers.base_provider import StandardJob
from src.integrations.apify_manager import ApifyManager
from src.config.config import Config

class LinkedInJobsProvider:
    def __init__(self):
        self._pipeline_type = 'PIPELINE_B'
        self.manager = ApifyManager()
        self.actor_id = Config.APIFY_ACTOR_ID or "hKByXkMQaC5Qt9UMN"
        
    def _load_preferences(self) -> dict:
        try:
            with open("src/config/user_preferences.yaml", "r") as f:
                return yaml.safe_load(f)
        except Exception:
            # Fallback preferences
            return {
                "target_roles": ["Product Manager", "Software Engineer"],
                "locations": ["India"]
            }

    # Maps internal role slugs → human-readable LinkedIn search terms
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

    def _generate_urls(self, prefs: dict) -> List[str]:
        roles = prefs.get("target_roles", ["Software Engineer"])
        locations = prefs.get("locations", ["India"])
        urls = []
        for role in roles:
            # Convert slug -> human readable (e.g. associate_product_manager -> "Associate Product Manager")
            label = self.ROLE_LABELS.get(role, role.replace("_", " ").title())
            for loc in locations:
                query = urllib.parse.quote(label)
                location = urllib.parse.quote(loc)
                # f_E=2  → Entry Level only
                # f_TPR=r604800 → posted in past 7 days
                url = (
                    f"https://www.linkedin.com/jobs/search/"
                    f"?keywords={query}&location={location}"
                    f"&f_E=2&f_TPR=r604800"
                )
                urls.append(url)
        return urls

    def _discover_jobs_internal(self, last_sync_timestamp: Optional[str]) -> List[StandardJob]:
        prefs = self._load_preferences()
        urls = self._generate_urls(prefs)

        # Cap URLs per run to conserve Apify credits (~$0.001/result)
        # 9 roles × 2 locations = 18 combos — limit to 6 per run, rotate via cursor
        MAX_URLS_PER_RUN = 6
        start_idx = 0
        if last_sync_timestamp and last_sync_timestamp.isdigit():
            start_idx = int(last_sync_timestamp) % len(urls)
        urls_this_run = (urls[start_idx:] + urls[:start_idx])[:MAX_URLS_PER_RUN]
        next_cursor = str((start_idx + MAX_URLS_PER_RUN) % len(urls))

        client, key_id = self.manager.get_client(tier=4, category="linkedin_pipeline_b")
        if not client:
            raise Exception("No Apify client available for LinkedIn jobs")

        logger.info(
            f"LinkedInJobsProvider: Searching {len(urls_this_run)} URLs "
            f"(entry-level, past 7 days, {[u.split('keywords=')[1].split('&')[0] for u in urls_this_run]})"
        )

        run_input = {
            "urls": urls_this_run,
            "maxItems": 25  # 25 results per run = ~$0.025, tight budget
        }
        
        try:
            run = client.actor(self.actor_id).call(run_input=run_input)
        except Exception as e:
            err_str = str(e)
            if "Monthly usage hard limit exceeded" in err_str or "monthly" in err_str.lower():
                logger.warning(f"LinkedInJobsProvider: Key {key_id} hit monthly limit — marking as RATE_LIMITED")
                import sqlite3
                from src.config.config import Config
                try:
                    conn = sqlite3.connect(Config.DATABASE_PATH)
                    conn.execute("UPDATE apify_keys SET status = 'RATE_LIMITED' WHERE id = ?", (key_id,))
                    conn.commit()
                    conn.close()
                except Exception:
                    pass
            raise

        # Apify SDK v3+ returns a typed object; extract dataset ID from it
        dataset_id = getattr(run, "default_dataset_id", None)
        if not dataset_id:
            dataset_id = getattr(run, "defaultDatasetId", None)
        if not dataset_id and isinstance(run, dict):
            dataset_id = run.get("defaultDatasetId") or run.get("default_dataset_id")

        if not dataset_id:
            self.manager.record_usage(key_id, "linkedin_pipeline_b", credits=0, useful_results=0, success=False)
            raise Exception("Apify Run did not return a dataset ID")
            
        jobs = []
        for item in client.dataset(dataset_id).iterate_items():
            title = item.get("title", "Unknown")
            company = item.get("companyName", "Unknown")
            url = item.get("link", "")
            
            # Simple exclusion filter
            exclude_keywords = prefs.get("exclude_keywords", ["senior", "lead", "director", "manager"])
            title_lower = title.lower()
            if any(exc.lower() in title_lower for exc in exclude_keywords if exc.strip()):
                continue
                
            jobs.append(StandardJob(
                company=company,
                role=title,
                location=item.get("location", "Unknown"),
                remote_hybrid_onsite="Unknown",
                experience_required=item.get("seniorityLevel", ""),
                skills=[],
                job_description=item.get("descriptionText", ""),
                ats_type="linkedin",
                application_url=url,
                source="linkedin_jobs",
                date_posted=item.get("postedAt", datetime.now().isoformat())
            ))
            
        self.manager.record_usage(key_id, "linkedin_pipeline_b", credits=0.025, useful_results=len(jobs), success=True)
        return jobs, next_cursor
