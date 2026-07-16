from src.api.db import get_connection
import asyncio
import aiohttp
import time
import logging
from typing import List
from src.config.config import Config
from src.discovery.pipeline.ats_registry import ATSRegistry
from src.jobs.registry import JobRegistry
from src.discovery.pipeline.plugins.workday_plugin import WorkdayDiscoveryPlugin

logger = logging.getLogger("JobCrawlerOrchestrator")

class JobCrawlerOrchestrator:
    def __init__(self):
        self.ats_registry = ATSRegistry()
        self.job_registry = JobRegistry()
        # In the future, this would be a map or instantiated from a PluginManager
        self.plugins = {
            'workday': WorkdayDiscoveryPlugin()
        }
        
    async def run_sync(self, limit: int = 20):
        """
        Pulls ACTIVE endpoints from the registry that are due for a job crawl,
        crawls them using the appropriate plugin, normalizes the jobs,
        and saves them to the JobRegistry.
        """
        import sqlite3
        now = time.time()
        
        # 1. Fetch endpoints that are active
        # In a real system, we'd check `last_job_sync + plugin.crawl_policy() < now`
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, company_id, ats_type, canonical_endpoint, last_job_sync FROM ats_registry WHERE status = 'ACTIVE' LIMIT ?",
                (limit,)
            ).fetchall()
            
        if not rows:
            logger.info("No active endpoints found to crawl.")
            return

        async with aiohttp.ClientSession() as session:
            for row in rows:
                endpoint_id = row['id']
                company_id = row['company_id']
                ats_type = row['ats_type']
                endpoint = row['canonical_endpoint']
                
                plugin = self.plugins.get(ats_type)
                if not plugin:
                    logger.warning(f"No crawler plugin found for ATS type: {ats_type}")
                    continue
                    
                logger.info(f"Crawling jobs for {company_id} ({ats_type}) at {endpoint}")
                crawl_version = int(now)
                
                # Crawl
                try:
                    crawl_result = await plugin.crawl_jobs(endpoint, session=session)
                    
                    if crawl_result.errors > 0 and not crawl_result.jobs:
                        logger.error(f"Crawl failed for {company_id}: {crawl_result.errors} errors.")
                        # Could update crawl_status to FAILED on ats_registry here
                        continue
                        
                    # Normalize
                    normalized_jobs = []
                    for raw_job in crawl_result.jobs:
                        try:
                            # Workday plugin accepts endpoint to construct full apply URLs
                            job = plugin.normalize_job(raw_job, company_id, endpoint)
                            normalized_jobs.append(job)
                        except Exception as e:
                            logger.error(f"Failed to normalize job for {company_id}: {str(e)}")
                            
                    # Update Job Registry
                    self.job_registry.sync_jobs(company_id, ats_type, normalized_jobs, crawl_version)
                    
                    # Update ATS Registry sync stats
                    with get_connection() as conn:
                        conn.execute("""
                            UPDATE ats_registry SET 
                                last_job_sync = ?, 
                                last_successful_crawl = ?, 
                                job_count = ?
                            WHERE id = ?
                        """, (now, now, len(normalized_jobs), endpoint_id))
                        conn.commit()
                        
                    logger.info(f"Successfully synced {len(normalized_jobs)} jobs for {company_id}.")
                    
                except Exception as e:
                    logger.error(f"Unexpected error crawling {company_id}: {str(e)}")
