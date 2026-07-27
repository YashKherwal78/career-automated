import os
import sys
import subprocess
import logging
from src.database.migrate import MigrationRunner
from src.config.settings import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Launcher")

if __name__ == "__main__":
    logger.info("CareerAutomated Pipeline Launcher Starting...")
    
    # 1. Database Migrations
    try:
        runner = MigrationRunner(settings.db_path)
        runner.run_migrations()
    except Exception as e:
        logger.warning(f"Failed to run database migrations (ignoring for SQLite Phase 2B): {e}")

    # 2. Configuration Validation
    logger.info(f"Database validated at: {settings.db_path}")
    logger.info(f"Feature Flags: Discovery={settings.enable_discovery}, Verification={settings.enable_verification}, Crawler={settings.enable_crawler}")

    try:
        # Launch mass_scheduler using sys.executable to run inside the virtual environment
        subprocess.run([sys.executable, "-m", "src.workers.mass_scheduler"])
    except KeyboardInterrupt:
        logger.info("Launcher interrupted. Exiting.")
