import uuid
import time
import requests
from typing import List, Dict, Any
from src.discovery.providers.base_discovery_provider import BaseDiscoveryProvider, OpportunitySeed
from src.crm.database import get_connection

class CompanyIntelligenceProvider(BaseDiscoveryProvider):
    def __init__(self):
        super().__init__()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
        }

    def fetch_greenhouse(self, slug: str) -> List[Dict]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("jobs", [])
        except Exception:
            pass
        return []

    def fetch_lever(self, slug: str) -> List[Dict]:
        url = f"https://api.lever.co/v0/postings/{slug}"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return []

    def discover(self) -> List[OpportunitySeed]:
        seeds = []
        conn = get_connection()
        c = conn.cursor()
        
        # Get all companies
        c.execute('''
            SELECT c.company_name, c.website, c.ats_provider, c.greenhouse_slug, c.lever_slug 
            FROM company_intelligence_static c
        ''')
        companies = c.fetchall()
        
        strategy_id = str(uuid.uuid4())
        start_time = time.time()
        
        for row in companies:
            company_name = row[0]
            website = row[1]
            ats = row[2]
            gh_slug = row[3]
            lever_slug = row[4]
            
            jobs_fetched = 0
            pm_count = 0
            apm_count = 0
            ai_count = 0
            founder_count = 0
            
            try:
                if gh_slug:
                    jobs = self.fetch_greenhouse(gh_slug)
                    for j in jobs:
                        title = j.get("title", "")
                        seeds.append(OpportunitySeed(
                            source="company_intelligence",
                            ats="greenhouse",
                            company_name=company_name,
                            job_url=j.get("absolute_url", ""),
                            job_title=title,
                            discovered_query="intelligence_sync",
                            confidence=1.0,
                            strategy_id=strategy_id
                        ))
                        jobs_fetched += 1
                        
                        tl = title.lower()
                        if "associate product manager" in tl or "apm" in tl:
                            apm_count += 1
                        elif "product manager" in tl:
                            pm_count += 1
                        if "ai " in tl or "artificial intelligence" in tl:
                            ai_count += 1
                        if "founder" in tl:
                            founder_count += 1

                elif lever_slug:
                    jobs = self.fetch_lever(lever_slug)
                    for j in jobs:
                        title = j.get("text", "")
                        seeds.append(OpportunitySeed(
                            source="company_intelligence",
                            ats="lever",
                            company_name=company_name,
                            job_url=j.get("hostedUrl", ""),
                            job_title=title,
                            discovered_query="intelligence_sync",
                            confidence=1.0,
                            strategy_id=strategy_id
                        ))
                        jobs_fetched += 1
                        
                        tl = title.lower()
                        if "associate product manager" in tl or "apm" in tl:
                            apm_count += 1
                        elif "product manager" in tl:
                            pm_count += 1
                        if "ai " in tl or "artificial intelligence" in tl:
                            ai_count += 1
                        if "founder" in tl:
                            founder_count += 1
                            
                # Update dynamic table
                c.execute('''
                    UPDATE hiring_intelligence_dynamic
                    SET last_successful_sync = CURRENT_TIMESTAMP,
                        last_checked = CURRENT_TIMESTAMP,
                        active_job_count = ?,
                        pm_job_count = ?,
                        apm_job_count = ?,
                        ai_job_count = ?,
                        founder_office_job_count = ?,
                        consecutive_failures = 0
                    WHERE company_name = ?
                ''', (jobs_fetched, pm_count, apm_count, ai_count, founder_count, company_name))
                
            except Exception as e:
                c.execute('''
                    UPDATE hiring_intelligence_dynamic
                    SET last_checked = CURRENT_TIMESTAMP,
                        last_error = ?,
                        consecutive_failures = consecutive_failures + 1
                    WHERE company_name = ?
                ''', (str(e), company_name))
                
        conn.commit()
        conn.close()
        
        return seeds
