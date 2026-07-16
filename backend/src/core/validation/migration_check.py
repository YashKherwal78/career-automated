import logging
from src.core.repositories.manager import RepositoryManager
from src.api.db import is_postgres

logger = logging.getLogger("migration_check")

def run_migration_validation(repos: RepositoryManager) -> bool:
    """
    Validates that the database schema is fully initialized and migrations have run.
    """
    try:
        with repos.transaction() as conn:
            # 1. Check schema_version exists
            if is_postgres():
                cur = conn.execute("SELECT to_regclass('public.schema_version')")
                if not cur.fetchone()[0]:
                    logger.error("schema_version table is missing")
                    return False
            else:
                cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'")
                if not cur.fetchone():
                    logger.error("schema_version table is missing")
                    return False

            # 2. Check schema_version number (Assuming at least version 1 or recent version)
            cur = conn.execute("SELECT version FROM schema_version ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            if not row:
                logger.error("No migrations recorded in schema_version")
                return False
            
            # 3. Check core state tables
            required_tables = [
                "worker_states", "company_identities", "ats_registry",
                "normalized_jobs", "local_queues"
            ]
            
            for table in required_tables:
                if is_postgres():
                    cur = conn.execute(f"SELECT to_regclass('public.{table}')")
                    if not cur.fetchone()[0]:
                        logger.error(f"Required table {table} is missing")
                        return False
                else:
                    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                    if not cur.fetchone():
                        logger.error(f"Required table {table} is missing")
                        return False
            
            logger.info("Migration validation passed.")
            return True
    except Exception as e:
        logger.error(f"Migration validation failed with error: {e}")
        return False
