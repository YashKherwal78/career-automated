from typing import List, Optional
import time
from datetime import datetime
from src.discovery.providers.base_provider import BaseProvider, StandardJob, ProviderCapabilities
from src.crm.database import get_connection, add_discovery_source
from src.discovery.ats_detector import ATSDetector
from src.discovery.company_intelligence_engine import CompanyIntelligenceEngine
from src.discovery.query_generator import QueryGenerator

class IndeedProvider(BaseProvider):
    def __init__(self):
        super().__init__()
        self.ats_detector = ATSDetector()
        self.intelligence_engine = CompanyIntelligenceEngine()
        self.query_generator = QueryGenerator()

    def _get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            requires_api_key=False, # We might switch to Apify later
            rate_limit_per_minute=5,
            supports_pagination=True,
            supports_incremental_sync=True,
            supports_remote_jobs=True,
            supports_search_filters=True
        )

    def validate_configuration(self) -> bool:
        return True

    def _check_company_exists(self, company_name: str) -> bool:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT 1 FROM company_intelligence_static WHERE company_name = ?", (company_name,))
        exists = c.fetchone() is not None
        conn.close()
        return exists

    def _register_new_company(self, company_name: str, website: str = None):
        # 1. Create NEW registry entry
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT OR IGNORE INTO company_intelligence_static 
            (company_name, careers_url, lifecycle_status, discovery_source)
            VALUES (?, ?, 'NEW', 'Indeed')
        ''', (company_name, website))
        conn.commit()
        conn.close()

        # 2. Trigger ATS Detector (mocking the career page search for now)
        if website:
            detection = self.ats_detector.detect_ats(website)
            if detection["ats_provider"] != "unknown":
                conn = get_connection()
                c = conn.cursor()
                ats = detection["ats_provider"]
                slug = detection["slug"]
                gh_slug = slug if ats == "greenhouse" else None
                lever_slug = slug if ats == "lever" else None
                ashby_slug = slug if ats == "ashby" else None
                
                c.execute('''
                    UPDATE company_intelligence_static
                    SET ats_provider = ?, greenhouse_slug = ?, lever_slug = ?, ashby_slug = ?, lifecycle_status = 'ATS_FOUND'
                    WHERE company_name = ?
                ''', (ats, gh_slug, lever_slug, ashby_slug, company_name))
                conn.commit()
                conn.close()

        # 3. Immediately compute Company Intelligence
        self.intelligence_engine.compute_all()

    def _discover_jobs_internal(self, last_sync_timestamp: Optional[str], target_companies: Optional[List[dict]] = None) -> List[StandardJob]:
        print("IndeedProvider: Starting discovery loop via QueryGenerator...")
        jobs_found = []
        
        queries = self.query_generator.generate_indeed_queries()
        
        for q in queries:
            # Sits above backend - checks cache first
            response = self.cache.fetch(
                provider_name="indeed",
                query=q["q"],
                location=q["l"],
                ttl_minutes=120
            )
            
            raw_jobs = response.get("results", [])
            for raw_job in raw_jobs:
                comp_name = raw_job["company"]
            
            # Check if company exists
            exists = self._check_company_exists(comp_name)
            if exists:
                # Add discovery source to boost confidence
                add_discovery_source(comp_name, "Indeed")
            else:
                # Register new company, run ATS detector, run intelligence engine
                self._register_new_company(comp_name, raw_job.get("website"))
                add_discovery_source(comp_name, "Indeed")
                
            jobs_found.append(
                StandardJob(
                    company=comp_name,
                    role=raw_job["role"],
                    location=raw_job["location"],
                    remote_hybrid_onsite=raw_job["remote"],
                    experience_required=raw_job["experience"],
                    skills=[],
                    job_description=raw_job["description"],
                    ats_type="unknown", # We don't apply through Indeed
                    application_url=raw_job["url"],
                    source="indeed_provider",
                    date_posted=raw_job["date_posted"]
                )
            )
            
        return jobs_found
