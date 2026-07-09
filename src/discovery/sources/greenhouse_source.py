from src.system.logger import setup_logger
logger = setup_logger('greenhouse_source')
import time
import random
import requests
from typing import List, Dict, Any
from src.discovery.sources.base import BaseDiscoverySource

class GreenhouseSource(BaseDiscoverySource):
    """
    Pure retrieval component for Greenhouse.
    Takes verified slugs and returns normalized Opportunity objects.
    """
    def __init__(self):
        self.base_url = "https://boards-api.greenhouse.io/v1/boards"

    def get_job(self, slug: str, job_id: str) -> list:
        url = f"{self.base_url}/{slug}/jobs/{job_id}"
        logger.info(f"GreenhouseSource: Direct extracting {slug} job {job_id}...")
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                job_data = response.json()
                # Parse to match opportunity format
                loc = job_data.get('location', {}).get('name', 'Unknown Location')
                opp = {
                    "title": job_data.get("title"),
                    "company": slug,  # we use slug as company fallback for now
                    "source": "greenhouse",
                    "url": job_data.get("absolute_url"),
                    "ats": "greenhouse",
                    "location": loc,
                    "remote": "remote" in loc.lower(),
                    "experience": "Unknown",
                    "posted_date": job_data.get("updated_at")
                }
                return [opp]
            else:
                logger.info(f"  -> Failed to fetch {job_id}. Status: {response.status_code}")
                return []
        except Exception as e:
            logger.info(f"  -> Error fetching {job_id}: {e}")
            return []

    def discover_opportunities(self, slugs: List[str]) -> List[Dict[str, Any]]:
        opportunities = []
        logger.info(f"GreenhouseSource: Starting opportunity retrieval for {len(slugs)} slugs...")
        
        for slug in slugs:
            url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    jobs = data.get("jobs", [])
                    logger.info(f"GreenhouseSource: Retrieved {len(jobs)} raw jobs from {slug}")
                    
                    for job in jobs:
                        # Normalize to standard Opportunity object
                        location = job.get("location", {}).get("name", "Unknown")
                        opportunities.append({
                            "title": job.get("title", ""),
                            "company": slug,
                            "source": "Greenhouse",
                            "url": job.get("absolute_url", ""),
                            "ats": "GREENHOUSE",
                            "location": location,
                            "experience": "Unknown", # Extracted in prefilter if needed
                            "remote": "remote" in location.lower(),
                            "posted_date": job.get("updated_at", ""),
                            "description": "Fetched via Greenhouse API", # Minimal overhead
                            "discovery_timestamp": time.time()
                        })
                else:
                    logger.info(f"GreenhouseSource: Failed to fetch {slug} - HTTP {response.status_code}")
            except Exception as e:
                logger.info(f"GreenhouseSource: Error fetching {slug}: {e}")
            
            # Rate limiting
            time.sleep(random.uniform(0.3, 0.5))
            
        return opportunities
