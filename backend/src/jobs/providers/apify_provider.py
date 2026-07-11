from src.system.logger import setup_logger
logger = setup_logger('apify_provider')
import urllib.parse
from typing import List, Dict
from datetime import datetime
from src.config.config import Config
from src.jobs.providers.base_provider import JobProvider
from src.integrations.apify_manager import ApifyManager

class ApifyProvider(JobProvider):
    def __init__(self):
        self.manager = ApifyManager()
        self.actor_id = Config.APIFY_ACTOR_ID

    def _generate_urls(self) -> List[str]:
        roles = [
            "AI Engineer",
            "Machine Learning Engineer",
            "LLM Engineer",
            "GenAI Engineer",
            "Software Engineer",
            "Backend Engineer",
            "Associate Product Manager",
            "Product Analyst",
            "Data Analyst",
            "AI Product Manager"
        ]
        locations = ["India", "Remote"]
        urls = []
        for role in roles:
            for loc in locations:
                query = urllib.parse.quote(role)
                location = urllib.parse.quote(loc)
                url = f"https://www.linkedin.com/jobs/search/?keywords={query}&location={location}"
                urls.append(url)
        return urls

    def discover_jobs(self) -> List[Dict]:
        jobs = []
        try:
            client, key_id = self.manager.get_client(tier=4, category="job_discovery")
            if not client:
                logger.info("ApifyProvider: Discovery skipped (Budget limit reached or no active keys).")
                return []
                
            logger.info(f"ApifyProvider: Starting Apify actor {self.actor_id} via Manager...")
            
            urls = self._generate_urls()
            
            run_input = {
                "urls": urls,
                "maxItems": 10 # Testing/initial run limit
            }
            
            # Run the actor
            run = client.actor(self.actor_id).call(run_input=run_input)
            
            dataset_id = getattr(run, "default_dataset_id", getattr(run, "defaultDatasetId", None))
            if not dataset_id and isinstance(run, dict):
                dataset_id = run.get("defaultDatasetId") or run.get("default_dataset_id")
            
            if not dataset_id:
                logger.info("ApifyProvider: Could not find dataset ID in run response.")
                self.manager.record_usage(key_id, "job_discovery", credits=0.0, useful_results=0, success=False)
                return []
                
            # Fetch and process results
            for item in client.dataset(dataset_id).iterate_items():
                posted_date_str = item.get("postedAt", datetime.now().isoformat())
                days_old = 0
                if posted_date_str:
                    try:
                        # Extract YYYY-MM-DD
                        date_part = posted_date_str.split("T")[0]
                        posted_date = datetime.strptime(date_part, "%Y-%m-%d")
                        days_old = (datetime.now() - posted_date).days
                        # Fallback for future dates or minor timezone issues
                        if days_old < 0:
                            days_old = 0
                    except Exception:
                        pass
                
                job_title_lower = item.get("title", "").lower()
                desc_lower = item.get("descriptionText", item.get("descriptionHtml", "")).lower()
                
                # Exclusion filters
                exclusions = ["senior", "lead", "principal", "staff", "manager", "director", "3+ years", "4+ years", "5+ years", "6+ years", "7+ years"]
                skip_job = False
                for exclude in exclusions:
                    if exclude in job_title_lower or exclude in desc_lower:
                        skip_job = True
                        break
                        
                if skip_job:
                    continue
                
                job = {
                    "company_name": item.get("companyName", ""),
                    "job_title": item.get("title", ""),
                    "job_url": item.get("link", ""),
                    "job_description": item.get("descriptionText", item.get("descriptionHtml", "")),
                    "location": item.get("location", ""),
                    "experience_required": item.get("seniorityLevel", ""),
                    "skills_required": item.get("skills", ""), # Natively doesn't extract this out of the box in this actor but keeping schema
                    "employment_type": item.get("employmentType", ""),
                    "posting_date": posted_date_str,
                    "days_old": days_old
                }
                jobs.append(job)
                
            logger.info(f"ApifyProvider: Successfully fetched {len(jobs)} jobs.")
            
            # Record usage (assuming standard actor run cost of ~0.05 credits for a small run)
            self.manager.record_usage(key_id, "job_discovery", credits=0.05, useful_results=len(jobs), success=True)
            
        except Exception as e:
            logger.info(f"Error reading from Apify provider: {e}")
            if 'key_id' in locals():
                self.manager.record_usage(key_id, "job_discovery", credits=0.0, useful_results=0, success=False)
            
        return jobs
