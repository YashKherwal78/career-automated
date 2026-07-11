from src.system.logger import setup_logger
logger = setup_logger('workable_provider')
import requests
import sqlite3
import datetime
import re
from typing import List
from bs4 import BeautifulSoup

from src.discovery.providers.base_provider import BaseProvider, StandardJob, ProviderCapabilities
from src.config.config import Config

class WorkableProvider(BaseProvider):
    def __init__(self):
        super().__init__()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
    def _get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities()
        
    def _discover_jobs_internal(self, target_roles: list = None) -> List[StandardJob]:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        c = conn.cursor()
        c.execute("""
            SELECT company_name, workable_slug 
            FROM company_intelligence_static 
            WHERE lower(ats_provider) = 'workable' AND workable_slug IS NOT NULL
        """)
        companies = c.fetchall()
        conn.close()
        
        jobs = []
        for company, slug in companies:
            logger.info(f"Fetching Workable for {company} ({slug})...")
            # Workable has a public API / jobs endpoint
            url = f"https://apply.workable.com/api/v3/accounts/{slug}/jobs"
            try:
                # Need to send POST for their jobs API usually, or just parse HTML
                # Often it's a POST to https://apply.workable.com/api/v3/accounts/{slug}/jobs
                resp = requests.post(url, json={"query": "", "location": [], "department": [], "worktype": [], "remote": []}, headers=self.headers, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get('results', []):
                        job_url = f"https://apply.workable.com/{slug}/j/{item.get('shortcode')}"
                        jobs.append(StandardJob(
                            role=item.get('title', ''),
                            company=company,
                            location=item.get('location', {}).get('countryName', 'Unknown'),
                            remote_hybrid_onsite='Unknown',
                            experience_required='Unknown',
                            skills=[],
                            job_description=item.get('description', ''),
                            application_url=job_url,
                            ats_type="workable",
                            source="Workable",
                            date_posted=item.get('published_on', datetime.datetime.now().isoformat())
                        ))
            except Exception as e:
                logger.info(f"Workable fail for {company}: {e}")
                
        return jobs
