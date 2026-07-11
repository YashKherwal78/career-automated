from src.system.logger import setup_logger
logger = setup_logger('generic_careers_provider')
import requests
import sqlite3
import datetime
from typing import List
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from src.discovery.providers.base_provider import BaseProvider, StandardJob, ProviderCapabilities
from src.config.config import Config

class GenericCareersProvider(BaseProvider):
    def __init__(self):
        super().__init__()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    def _get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities()
        
    def _discover_jobs_internal(self, target_roles: list = None) -> List[StandardJob]:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        c = conn.cursor()
        c.execute("""
            SELECT company_name, website, careers_url 
            FROM company_intelligence_static 
            WHERE lower(ats_provider) = 'generic'
        """)
        companies = c.fetchall()
        conn.close()
        
        jobs = []
        for company, website, careers_url in companies:
            logger.info(f"Fetching Generic Careers for {company}...")
            url = careers_url if careers_url else (f"{website.rstrip('/')}/careers" if website else "")
            if not url:
                continue
                
            try:
                resp = requests.get(url, headers=self.headers, timeout=10)
                if resp.status_code != 200:
                    continue
                    
                soup = BeautifulSoup(resp.text, 'html.parser')
                links = soup.find_all('a', href=True)
                
                # Simple heuristic: Look for links with "job", "career", "role", or "position" in them
                # or links that match standard job post formats like /jobs/12345
                found_links = set()
                
                for link in links:
                    href = link['href']
                    text = link.get_text(strip=True).lower()
                    full_url = urljoin(url, href)
                    
                    is_job_link = False
                    if '/job/' in href or '/role/' in href or '/careers/' in href or '/position/' in href:
                        # Make sure it's not just a generic page link
                        if len(href.split('/')) > 2:
                            is_job_link = True
                            
                    # Some sites use query params ?job_id=123
                    if 'job' in href and '=' in href:
                        is_job_link = True
                        
                    if is_job_link and full_url not in found_links:
                        found_links.add(full_url)
                        
                        jobs.append(StandardJob(
                            role=link.get_text(strip=True) or "Unknown Role",
                            company=company,
                            location="Unknown",
                            remote_hybrid_onsite="Unknown",
                            experience_required="Unknown",
                            skills=[],
                            job_description="",
                            application_url=full_url,
                            ats_type="generic",
                            source="Generic",
                            date_posted=datetime.datetime.now().isoformat()
                        ))
            except Exception as e:
                logger.info(f"Generic Careers fail for {company}: {e}")
                
        return jobs
