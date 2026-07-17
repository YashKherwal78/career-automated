import time
import logging
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger("PipelineStateManager")

# Canonical Pipeline States
VALID_LIFECYCLE_STATES = {
    "DISCOVERED",
    "VERIFICATION_PENDING",
    "VERIFYING",
    "VERIFIED",
    "CRAWL_PENDING",
    "CRAWLING",
    "ACTIVE",
    # Failure states
    "VERIFICATION_FAILED",
    "CRAWL_FAILED",
    "NORMALIZATION_FAILED",
    "RATE_LIMITED",
    "BOT_BLOCKED",
    "ATS_CHANGED",
    "RETRY_PENDING",
    "MANUAL_REVIEW"
}

# Strict Transition Rules
VALID_TRANSITIONS = {
    "DISCOVERED": {"VERIFICATION_PENDING", "VERIFIED"},  # VERIFIED for Fast Path
    "VERIFICATION_PENDING": {"VERIFYING"},
    "VERIFYING": {"VERIFIED", "VERIFICATION_FAILED"},
    "VERIFIED": {"CRAWL_PENDING"},
    "CRAWL_PENDING": {"CRAWLING"},
    "CRAWLING": {"ACTIVE", "CRAWL_FAILED", "CRAWL_PENDING", "CRAWLING"},
    "ACTIVE": {"ACTIVE", "CRAWL_PENDING", "CRAWLING", "CRAWL_FAILED"}
}

VALID_HEALTH_STATES = {
    "HEALTHY",
    "STALE",
    "RATE_LIMITED",
    "BOT_BLOCKED",
    "ERROR"
}

class TransitionError(Exception):
    pass

class PipelineStateManager:
    @staticmethod
    def _validate_transition(current_state: Optional[str], to_state: str):
        if to_state not in VALID_LIFECYCLE_STATES:
            raise TransitionError(f"Invalid state: {to_state}")
            
        # Allow initial transition to DISCOVERED
        if not current_state and to_state == "DISCOVERED":
            return
            
        if current_state and current_state in VALID_TRANSITIONS:
            if to_state not in VALID_TRANSITIONS[current_state]:
                raise TransitionError(f"Illegal transition: {current_state} -> {to_state}")

    @staticmethod
    def transition(
        company_id: str,
        to_state: str,
        health_state: Optional[str] = None,
        failure_reason: Optional[str] = None,
        crawl_status: Optional[str] = None,
        verification_method: Optional[str] = None,
        queue_op: Optional[Dict[str, Any]] = None,
        conn = None
    ) -> bool:
        """
        Executes a lifecycle transition atomically within a single database transaction.
        Optionally executes a queue push in the same transaction.
        """
        from src.api.db import get_connection, is_postgres
        import json
        
        db_conn = conn or get_connection()
        try:
            db_conn.execute("BEGIN TRANSACTION;" if not is_postgres() else "BEGIN;")
            
            # 1. Fetch current state
            if is_postgres():
                cur = db_conn.execute("SELECT lifecycle_state FROM company_identities WHERE company_id = %s FOR UPDATE", (company_id,))
            else:
                cur = db_conn.execute("SELECT lifecycle_state FROM company_identities WHERE company_id = ?", (company_id,))
            row = cur.fetchone()
            
            if not row:
                raise TransitionError(f"Company {company_id} not found in identities.")
                
            current_state = row["lifecycle_state"] if hasattr(row, 'keys') else row[0]
            
            # 2. Validate transition
            PipelineStateManager._validate_transition(current_state, to_state)
            
            # 3. Build update query
            updates = ["lifecycle_state = ?"]
            params = [to_state]
            
            if health_state:
                updates.append("health_state = ?")
                params.append(health_state)
            if failure_reason is not None:
                updates.append("failure_reason = ?")
                params.append(failure_reason)
            if crawl_status is not None:
                cs_query = "UPDATE ats_registry SET crawl_status = ? WHERE company_id = ?"
                if is_postgres():
                    cs_query = cs_query.replace("?", "%s")
                db_conn.execute(cs_query, (crawl_status, company_id))
            if verification_method is not None:
                updates.append("verification_method = ?")
                params.append(verification_method)
                
            params.append(company_id)
            
            query = f"UPDATE company_identities SET {', '.join(updates)} WHERE company_id = ?"
            if is_postgres():
                query = query.replace("?", "%s")
                
            db_conn.execute(query, tuple(params))
            
            # 4. Execute queue operation atomically
            if queue_op:
                queue_name = queue_op.get("queue_name")
                payload = queue_op.get("payload", {})
                priority = queue_op.get("priority", 0)
                
                payload_str = json.dumps(payload)
                import uuid
                item_id = str(uuid.uuid4())
                
                if is_postgres():
                    db_conn.execute(
                        """
                        INSERT INTO local_queues (item_id, queue_name, payload, status, created_at, locked_until, retry_count)
                        VALUES (%s, %s, %s, 'QUEUED', %s, 0.0, 0)
                        ON CONFLICT (item_id) DO NOTHING
                        """,
                        (item_id, queue_name, payload_str, time.time())
                    )
                else:
                    db_conn.execute(
                        """
                        INSERT OR IGNORE INTO local_queues (item_id, queue_name, payload, status, created_at, locked_until, retry_count)
                        VALUES (?, ?, ?, 'QUEUED', ?, 0.0, 0)
                        """,
                        (item_id, queue_name, payload_str, time.time())
                    )
            
            if not conn:
                db_conn.commit()
            return True
            
        except Exception as e:
            if not conn:
                db_conn.rollback()
            logger.error(f"Transition failed for {company_id}: {e}")
            raise e
        finally:
            if not conn:
                db_conn.close()

    @staticmethod
    def transition_batch(
        company_ids: List[str],
        to_state: str,
        health_state: Optional[str] = None,
        failure_reason: Optional[str] = None,
        crawl_status: Optional[str] = None,
        verification_method: Optional[str] = None,
        queue_op_name: Optional[str] = None,
        conn = None
    ) -> bool:
        """
        Executes a lifecycle transition for a batch of companies atomically.
        """
        if not company_ids:
            return True
            
        from src.api.db import get_connection, is_postgres
        import json
        
        db_conn = conn or get_connection()
        try:
            db_conn.execute("BEGIN TRANSACTION;" if not is_postgres() else "BEGIN;")
            
            # 1. Fetch current states to validate
            placeholders = ",".join(["?" if not is_postgres() else "%s"] * len(company_ids))
            cur = db_conn.execute(f"SELECT company_id, lifecycle_state FROM company_identities WHERE company_id IN ({placeholders})", tuple(company_ids))
            
            for row in cur.fetchall():
                cid = row["company_id"] if hasattr(row, 'keys') else row[0]
                c_state = row["lifecycle_state"] if hasattr(row, 'keys') else row[1]
                PipelineStateManager._validate_transition(c_state, to_state)
            
            # 2. Build update query
            updates = ["lifecycle_state = ?", "updated_at = ?"]
            params = [to_state, time.time()]
            
            if health_state:
                updates.append("health_state = ?")
                params.append(health_state)
            if failure_reason is not None:
                updates.append("failure_reason = ?")
                params.append(failure_reason)
            if crawl_status is not None:
                updates.append("crawl_status = ?")
                params.append(crawl_status)
            if verification_method is not None:
                updates.append("verification_method = ?")
                params.append(verification_method)
                
            query = f"UPDATE company_identities SET {', '.join(updates)} WHERE company_id IN ({placeholders})"
            if is_postgres():
                query = query.replace("?", "%s")
                
            full_params = tuple(params) + tuple(company_ids)
            db_conn.execute(query, full_params)
            
            # 3. Queue operations
            if queue_op_name:
                import uuid
                now = time.time()
                for cid in company_ids:
                    payload = {"company_id": cid}
                    payload_str = json.dumps(payload)
                    item_id = str(uuid.uuid4())
                    
                    if is_postgres():
                        db_conn.execute(
                            """
                            INSERT INTO local_queues (item_id, queue_name, payload, status, created_at, locked_until, retries)
                            VALUES (%s, %s, %s, 'QUEUED', %s, 0.0, 0)
                            ON CONFLICT (item_id) DO NOTHING
                            """,
                            (item_id, queue_op_name, payload_str, now)
                        )
                    else:
                        db_conn.execute(
                            """
                            INSERT OR IGNORE INTO local_queues (item_id, queue_name, payload, status, created_at, locked_until, retries)
                            VALUES (?, ?, ?, 'QUEUED', ?, 0.0, 0)
                            """,
                            (item_id, queue_op_name, payload_str, now)
                        )
            
            if not conn:
                db_conn.commit()
            return True
            
        except Exception as e:
            if not conn:
                db_conn.rollback()
            logger.error(f"Batch transition failed: {e}")
            raise e
        finally:
            if not conn:
                db_conn.close()
