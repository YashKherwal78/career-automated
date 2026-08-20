from src.api.db import get_connection
from src.system.logger import setup_logger
logger = setup_logger('linkedin_jobs_provider')
import yaml
import urllib.parse
from typing import List, Optional, Tuple
from datetime import datetime
from src.discovery.providers.base_provider import StandardJob
from src.discovery.providers.linkedin_guest_scraper import search_jobs_with_descriptions, LinkedInGuestBlocked
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

    # Same (role, location) pairs _generate_urls builds, kept in the same
    # roles-outer/locations-inner order so combos[i] always corresponds to
    # urls[i] -- the free scraper needs raw keywords+location, not a
    # pre-built LinkedIn search URL, but must land on the exact same
    # rotation cursor as the Apify fallback.
    def _generate_role_location_combos(self, prefs: dict) -> List[Tuple[str, str]]:
        roles = prefs.get("target_roles", ["Software Engineer"])
        locations = prefs.get("locations", ["India"])
        combos = []
        for role in roles:
            label = self.ROLE_LABELS.get(role, role.replace("_", " ").title())
            for loc in locations:
                combos.append((label, loc))
        return combos

    def _try_free_scraper(self, combos: List[Tuple[str, str]], exclude_keywords: list) -> Tuple[Optional[List[StandardJob]], bool]:
        """Tries LinkedIn's free, unauthenticated jobs-guest endpoints
        (linkedin_guest_scraper.py) before spending Apify credits. Returns
        (jobs, blocked) -- jobs is None ONLY if every combo in this run hit
        LinkedInGuestBlocked, signaling the caller to fall back to Apify.
        A combo that genuinely has zero matching jobs (no exception) is a
        successful free-scraper result, exactly like Apify returning an
        empty dataset -- it does not trigger a fallback."""
        jobs: List[StandardJob] = []
        blocked_count = 0
        for label, loc in combos:
            try:
                raw = search_jobs_with_descriptions(label, loc, f_e="2", f_tpr="r604800", max_results=25)
            except LinkedInGuestBlocked as e:
                logger.info(f"LinkedInJobsProvider: free scraper blocked for '{label}' in '{loc}': {e}")
                blocked_count += 1
                continue

            for item in raw:
                title = item.get("title", "Unknown")
                title_lower = title.lower()
                if any(exc.lower() in title_lower for exc in exclude_keywords if exc.strip()):
                    continue
                jobs.append(StandardJob(
                    company=item.get("company", "Unknown"),
                    role=title,
                    location=item.get("location", "Unknown"),
                    remote_hybrid_onsite="Unknown",
                    experience_required="",
                    skills=[],
                    job_description=item.get("description", ""),
                    ats_type="linkedin",
                    application_url=item.get("link", ""),
                    source="linkedin_jobs_guest",
                    date_posted=item.get("posted_at") or datetime.now().isoformat(),
                ))

        if combos and blocked_count == len(combos):
            return None, True
        return jobs, False

    def _discover_jobs_internal(self, last_sync_timestamp: Optional[str]) -> List[StandardJob]:
        prefs = self._load_preferences()
        urls = self._generate_urls(prefs)
        combos = self._generate_role_location_combos(prefs)

        # Cap URLs per run to conserve Apify credits (~$0.001/result) --
        # kept as the shared cap for the free scraper too, mainly to be
        # polite to LinkedIn's guest endpoint rather than for cost.
        # 9 roles × 2 locations = 18 combos — limit to 6 per run, rotate via cursor
        MAX_URLS_PER_RUN = 6
        start_idx = 0
        if last_sync_timestamp and last_sync_timestamp.isdigit():
            start_idx = int(last_sync_timestamp) % len(urls)
        urls_this_run = (urls[start_idx:] + urls[:start_idx])[:MAX_URLS_PER_RUN]
        combos_this_run = (combos[start_idx:] + combos[:start_idx])[:MAX_URLS_PER_RUN]
        next_cursor = str((start_idx + MAX_URLS_PER_RUN) % len(urls))

        exclude_keywords = prefs.get("exclude_keywords", ["senior", "lead", "director", "manager"])
        free_jobs, free_blocked = self._try_free_scraper(combos_this_run, exclude_keywords)
        if free_jobs is not None and not free_blocked:
            logger.info(
                f"LinkedInJobsProvider: free jobs-guest scraper returned {len(free_jobs)} jobs "
                f"for {len(combos_this_run)} combos — skipping Apify for this run."
            )
            return free_jobs, next_cursor

        logger.info("LinkedInJobsProvider: free jobs-guest scraper blocked/unavailable — falling back to Apify.")

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
                    conn = get_connection()
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
