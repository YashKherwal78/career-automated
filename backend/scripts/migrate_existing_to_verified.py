import os
import sys
import json
import logging
from typing import List, Dict, Any

# Ensure we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api.db import get_connection, is_postgres
from src.discovery.pipeline_state_manager import PipelineStateManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MigrationScript")

def migrate_existing_companies():
    conn = get_connection()
    try:
        # We need to find companies that are either:
        # 1. Already in ats_registry with status = 'ACTIVE'
        # 2. Have trusted metadata indicating a known ATS (like fast path)
        
        logger.info("Starting migration of existing companies...")
        
        # 1. Fetch all companies and their current states
        cursor = conn.cursor()
        if is_postgres():
            cursor.execute("""
                SELECT i.company_id, i.aliases, r.status as registry_status
                FROM company_identities i
                LEFT JOIN ats_registry r ON i.company_id = r.company_id AND r.status = 'ACTIVE'
            """)
        else:
            cursor.execute("""
                SELECT i.company_id, i.aliases, r.status as registry_status
                FROM company_identities i
                LEFT JOIN ats_registry r ON i.company_id = r.company_id AND r.status = 'ACTIVE'
            """)
            
        rows = cursor.fetchall()
        
        verified_companies = []
        fast_path_companies = []
        unverified_companies = []
        
        for row in rows:
            company_id = row["company_id"] if hasattr(row, 'keys') else row[0]
            aliases_str = row["aliases"] if hasattr(row, 'keys') else row[1]
            registry_status = row["registry_status"] if hasattr(row, 'keys') else row[2]
            
            metadata = {}
            if aliases_str:
                try:
                    metadata = json.loads(aliases_str)
                except:
                    pass
            
            # Check fast path criteria
            is_fast_path = (
                metadata.get("source") == "jobhive" and 
                metadata.get("known_ats") in ["greenhouse", "lever", "ashby", "workday", "smartrecruiters"]
            )
            
            if registry_status == 'ACTIVE':
                verified_companies.append(company_id)
            elif is_fast_path:
                fast_path_companies.append(company_id)
            else:
                unverified_companies.append(company_id)
                
        logger.info(f"Found {len(verified_companies)} companies with ACTIVE registry endpoints.")
        logger.info(f"Found {len(fast_path_companies)} companies with trusted fast-path metadata.")
        logger.info(f"Found {len(unverified_companies)} unverified companies.")
        
        # We need to transition the verified ones to VERIFIED and enqueue to crawl_queue
        # Since we might have already set them to DISCOVERED or something, we can force update them
        # Wait, PipelineStateManager enforces valid transitions. If a company is already VERIFIED, it might fail if we transition it from VERIFIED to VERIFIED.
        # Let's just execute raw SQL to fix their state to VERIFIED to avoid transition rules blocking the migration if they are in weird legacy states.
        
        logger.info("Migrating verified companies (registry)...")
        if verified_companies:
            if is_postgres():
                conn.execute(f"UPDATE company_identities SET lifecycle_state = 'VERIFIED', verification_method = 'IMPORTED_DATASET' WHERE company_id = ANY(%s)", (verified_companies,))
            else:
                placeholders = ",".join(["?"] * len(verified_companies))
                conn.execute(f"UPDATE company_identities SET lifecycle_state = 'VERIFIED', verification_method = 'IMPORTED_DATASET' WHERE company_id IN ({placeholders})", tuple(verified_companies))
            
            # Enqueue to crawl_queue
            _enqueue_batch(conn, "crawl_queue", verified_companies)
            
        logger.info("Migrating fast-path companies...")
        if fast_path_companies:
            if is_postgres():
                conn.execute(f"UPDATE company_identities SET lifecycle_state = 'VERIFIED', verification_method = 'FAST_PATH' WHERE company_id = ANY(%s)", (fast_path_companies,))
            else:
                placeholders = ",".join(["?"] * len(fast_path_companies))
                conn.execute(f"UPDATE company_identities SET lifecycle_state = 'VERIFIED', verification_method = 'FAST_PATH' WHERE company_id IN ({placeholders})", tuple(fast_path_companies))
                
            _enqueue_batch(conn, "crawl_queue", fast_path_companies)
            
        logger.info("Migrating unverified companies...")
        if unverified_companies:
            if is_postgres():
                conn.execute(f"UPDATE company_identities SET lifecycle_state = 'VERIFICATION_PENDING' WHERE company_id = ANY(%s)", (unverified_companies,))
            else:
                placeholders = ",".join(["?"] * len(unverified_companies))
                conn.execute(f"UPDATE company_identities SET lifecycle_state = 'VERIFICATION_PENDING' WHERE company_id IN ({placeholders})", tuple(unverified_companies))
                
            _enqueue_batch(conn, "verification_queue", unverified_companies)
            
        conn.commit()
        logger.info("Migration complete!")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        conn.close()

def _enqueue_batch(conn, queue_name: str, company_ids: List[str]):
    import time
    import uuid
    now = time.time()
    
    insert_data = []
    for cid in company_ids:
        payload = {"company_id": cid}
        payload_str = json.dumps(payload)
        item_id = str(uuid.uuid4())
        insert_data.append((item_id, queue_name, payload_str, 'QUEUED', now, 0.0, 0))
        
    if is_postgres():
        cursor = conn.cursor()
        # psycopg executemany is much faster for batches
        cursor.executemany(
            """
            INSERT INTO local_queues (item_id, queue_name, payload, status, created_at, locked_until, retry_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (item_id) DO NOTHING
            """,
            insert_data
        )
    else:
        conn.executemany(
            """
            INSERT OR IGNORE INTO local_queues (item_id, queue_name, payload, status, created_at, locked_until, retry_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            insert_data
        )

if __name__ == "__main__":
    migrate_existing_companies()
