from src.system.logger import setup_logger
logger = setup_logger('discovery')
import sqlite3
from src.config.config import Config
from src.discovery.providers.provider_manager import ProviderManager
from src.jobs.deduplicator import process_job
from src.jobs.ranking import apply_ranking_engine

def run_discovery_pipeline():
    """Pipeline A & B: Opportunity Discovery Engine"""
    logger.info("Agent 0: Initializing Dual Discovery Pipeline...")
    
    manager = ProviderManager()
    
    # We will pass empty dict for last_sync_timestamps for now
    logger.info("-> Running ProviderManager (Parallel Execution)...")
    opportunities = manager.run_all_providers()
    
    logger.info(f"-> Discovered {len(opportunities)} raw opportunities.")
    
    jobs_ingested = 0
    new_companies = 0
    
    conn = sqlite3.connect(Config.DATABASE_PATH)
    c = conn.cursor()
    
    for opt in opportunities:
        try:
            # Check if company exists in registry
            c.execute("SELECT 1 FROM company_intelligence_static WHERE company_name = ?", (opt.company,))
            exists = c.fetchone()
            
            if not exists and opt.company != "Unknown Company":
                # Dynamic Registration (Pipeline B)
                c.execute("""
                    INSERT INTO company_intelligence_static 
                    (company_name, priority, lifecycle_status, discovery_source) 
                    VALUES (?, 'P3', 'NEW', 'SEARCH_DISCOVERY')
                """, (opt.company,))
                conn.commit()
                new_companies += 1
                
            # Map StandardJob to the dictionary format expected by process_job
            # Map StandardJob to the dictionary format expected by process_job
            job_dict = {
                "company_name": opt.company,
                "job_title": opt.role,
                "job_url": opt.application_url,
                "job_description": opt.job_description,
                "location": opt.location,
                "experience_required": opt.experience_required,
                "skills_required": ", ".join(opt.skills) if opt.skills else "",
                "employment_type": opt.remote_hybrid_onsite,
                "posting_date": opt.date_posted,
                "source": opt.source
            }
            process_job(job_dict)
            jobs_ingested += 1
        except Exception as e:
            logger.info(f"Error processing opportunity {opt.role} at {opt.company}: {e}")
            
    conn.close()
    
    logger.info("-> Applying Opportunity Ranking (Phase 5)...")
    apply_ranking_engine()
    
    logger.info(f"Agent 0: Successfully ingested {jobs_ingested} opportunities into cache.")
    logger.info(f"Agent 0: Dynamically registered {new_companies} new P3 startups.")

if __name__ == "__main__":
    run_discovery_pipeline()
