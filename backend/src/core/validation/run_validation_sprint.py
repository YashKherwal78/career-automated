import time
import logging
from src.core.repositories.manager import RepositoryManager
from src.core.validation.migration_check import run_migration_validation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("validation_sprint")

def run_pre_flight_checks():
    repos = RepositoryManager()
    
    logger.info("Running Migration Validation Check...")
    if not run_migration_validation(repos):
        logger.error("Migration validation failed! Do not start the scheduler.")
        return False
        
    logger.info("Migration validation passed. System is ready for SQLite Production Validation Sprint.")
    logger.info("Next Steps for Validation:")
    logger.info("1. Start the Mass Scheduler and let it run for a few hours.")
    logger.info("   - Verify no orphan locks.")
    logger.info("   - Verify worker heartbeats update correctly.")
    logger.info("   - Verify next_crawl advances and adaptive tiers work.")
    logger.info("2. Trigger a Job Synchronization on a verified company.")
    logger.info("   - Confirm correct diffing (inserted, updated, archived).")
    logger.info("3. Check Mission Control to ensure all values are populated via API without mocks.")
    return True

if __name__ == "__main__":
    run_pre_flight_checks()
