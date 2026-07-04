import logging
from typing import Dict, Any
from src.discovery.priority_scheduler import PriorityScheduler
from src.discovery.providers.provider_manager import ProviderManager
from src.crm.database import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobDiscoveryEngine:
    """
    Job Discovery Engine V2
    This engine NEVER searches the open internet.
    It reads target companies from the PriorityScheduler, executes their specific ATS providers,
    extracts the jobs, and pushes them down the pipeline.
    """
    
    def __init__(self):
        self.scheduler = PriorityScheduler()
        self.provider_manager = ProviderManager()
        
    def run(self):
        logger.info("Starting Job Discovery Engine...")
        
        target_companies = self.scheduler.get_companies_to_scan(limit=100)
        
        if not target_companies:
            logger.info("No companies scheduled for scan.")
            return
            
        logger.info(f"Retrieved {len(target_companies)} companies to scan.")
        
        for company in target_companies:
            company_name = company['company_name']
            ats_provider = company.get('ats_provider', '').lower()
            
            if not ats_provider:
                logger.warning(f"Company {company_name} has no known ATS. Skipping.")
                continue
                
            logger.info(f"Scanning {company_name} via {ats_provider}...")
            
            # Use specific providers based on ats
            try:
                # We assume ProviderManager routes correctly based on ATS
                jobs = self.provider_manager.execute_providers(
                    query="", # No generic search query
                    location="",
                    limit_per_provider=50,
                    target_company=company_name,
                    ats_override=ats_provider,
                    careers_url=company.get('careers_url')
                )
            except Exception as e:
                logger.error(f"Error scanning {company_name}: {e}")
                self._update_hiring_intelligence(company_name, success=False, error=str(e))
                continue
                
            self._update_hiring_intelligence(company_name, success=True, jobs_found=len(jobs))
            logger.info(f"Discovered {len(jobs)} jobs for {company_name}.")
            
            # The jobs are now ready for EligibilityFilter, MatchEngine, etc.
            # In a real implementation, this would emit JobsDiscoveredEvent or similar.

    def _update_hiring_intelligence(self, company_name: str, success: bool, jobs_found: int = 0, error: str = None):
        """Updates the dynamic hiring intelligence with the results of the scan."""
        conn = get_connection()
        cursor = conn.cursor()
        
        if success:
            cursor.execute('''
                INSERT INTO hiring_intelligence_dynamic (company_name, last_successful_sync, last_checked, active_job_count, consecutive_failures, last_error)
                VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?, 0, NULL)
                ON CONFLICT(company_name) DO UPDATE SET
                last_successful_sync = CURRENT_TIMESTAMP,
                last_checked = CURRENT_TIMESTAMP,
                active_job_count = ?,
                consecutive_failures = 0,
                last_error = NULL
            ''', (company_name, jobs_found, jobs_found))
        else:
            cursor.execute('''
                INSERT INTO hiring_intelligence_dynamic (company_name, last_checked, consecutive_failures, last_error)
                VALUES (?, CURRENT_TIMESTAMP, 1, ?)
                ON CONFLICT(company_name) DO UPDATE SET
                last_checked = CURRENT_TIMESTAMP,
                consecutive_failures = consecutive_failures + 1,
                last_error = ?
            ''', (company_name, error, error))
            
        conn.commit()
        conn.close()

if __name__ == "__main__":
    engine = JobDiscoveryEngine()
    engine.run()
