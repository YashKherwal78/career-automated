import sqlite3
import json
import time
from typing import Any, Dict, Optional
from src.discovery.queue.base_queue import BaseQueue

class SQLiteQueue(BaseQueue):
    """
    SQLite-backed implementation of BaseQueue for local development.
    Uses a single table for all queues to mimic Redis lists.
    """
    
    def __init__(self, db_path: str = "data/crm.db"):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        from src.api.db import get_connection, is_postgres
        conn = get_connection()
        try:
            if not is_postgres():
                conn.execute('PRAGMA journal_mode=WAL')
                conn.execute('PRAGMA synchronous=NORMAL')
                conn.execute('PRAGMA busy_timeout=10000')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS local_queues (
                    item_id TEXT PRIMARY KEY,
                    queue_name TEXT NOT NULL,
                    payload JSON NOT NULL,
                    status TEXT DEFAULT 'QUEUED', -- QUEUED, PROCESSING, DEAD
                    failures INTEGER DEFAULT 0,
                    retry_count INTEGER DEFAULT 0,
                    error TEXT,
                    locked_until REAL DEFAULT 0.0,
                    next_retry_at REAL DEFAULT 0.0,
                    last_attempt_at REAL DEFAULT 0.0,
                    created_at REAL NOT NULL
                )
            ''')
            existing_cols = [row[1] for row in conn.execute("PRAGMA table_info(local_queues)")]
            if 'failures' not in existing_cols:
                conn.execute('ALTER TABLE local_queues ADD COLUMN failures INTEGER DEFAULT 0')
            if 'retry_count' not in existing_cols:
                conn.execute('ALTER TABLE local_queues ADD COLUMN retry_count INTEGER DEFAULT 0')
            if 'error' not in existing_cols:
                conn.execute('ALTER TABLE local_queues ADD COLUMN error TEXT')
            if 'next_retry_at' not in existing_cols:
                conn.execute('ALTER TABLE local_queues ADD COLUMN next_retry_at REAL DEFAULT 0.0')
            if 'last_attempt_at' not in existing_cols:
                conn.execute('ALTER TABLE local_queues ADD COLUMN last_attempt_at REAL DEFAULT 0.0')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_local_queues ON local_queues(queue_name, status, locked_until, next_retry_at)')
        finally:
            conn.close()
            
    def push(self, queue_name: str, payload: Dict[str, Any]) -> str:
        from src.api.db import get_connection
        import uuid
        item_id = str(uuid.uuid4())
        created_at = time.time()
        
        conn = get_connection()
        try:
            conn.execute('''
                INSERT INTO local_queues (
                    item_id, queue_name, payload, status, failures,
                    retry_count, error, locked_until, next_retry_at, last_attempt_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item_id, queue_name, json.dumps(payload), 'QUEUED', 0,
                0, None, 0.0, 0.0, 0.0, created_at
            ))
            conn.commit()
        finally:
            conn.close()
        return item_id
        
    def pop(self, queue_name: str, timeout: int = 0) -> Optional[Dict[str, Any]]:
        """
        Pops an item and locks it for 300 seconds.
        """
        from src.api.db import get_connection
        now = time.time()
        lock_until = now + 300.0 # 5 minute lock
        
        conn = get_connection()
        try:
            # Find the oldest available item that is due for retry
            cursor = conn.execute('''
                SELECT item_id, payload, status, failures, retry_count, error, locked_until,
                       next_retry_at, last_attempt_at, created_at
                FROM local_queues
                WHERE queue_name = ?
                  AND status = 'QUEUED'
                  AND locked_until <= ?
                  AND (next_retry_at IS NULL OR next_retry_at <= ?)
                ORDER BY created_at ASC LIMIT 1
            ''', (queue_name, now, now))
            row = cursor.fetchone()
            if not row:
                return None
            item_id, payload_str, status, failures, retry_count, error, locked_until_val, next_retry_at, last_attempt_at, created_at = row
            
            conn.execute('''
                UPDATE local_queues
                SET status = 'PROCESSING', locked_until = ?, last_attempt_at = ?
                WHERE item_id = ?
            ''', (lock_until, now, item_id))
            conn.commit()
            
            return {
                "_item_id": item_id,
                "payload": json.loads(payload_str),
                "status": status,
                "failures": failures,
                "retry_count": retry_count,
                "error": error,
                "locked_until": locked_until_val,
                "next_retry_at": next_retry_at,
                "last_attempt_at": last_attempt_at,
                "created_at": created_at,
                "queue_name": queue_name
            }
        finally:
            conn.close()
            
    def ack(self, queue_name: str, item_id: str) -> bool:
        """Deletes the item from the queue."""
        from src.api.db import get_connection
        conn = get_connection()
        try:
            cursor = conn.execute('DELETE FROM local_queues WHERE item_id = ? AND queue_name = ?', (item_id, queue_name))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
            
    def nack(self, queue_name: str, item_id: str, reason: str = "", backoff_seconds: int = 3600) -> bool:
        """Unlocks the item so it can be retried, applying a backoff."""
        from src.api.db import get_connection
        now = time.time()
        next_retry_at = now + backoff_seconds
        conn = get_connection()
        try:
            cursor = conn.execute('''
                UPDATE local_queues
                SET status = 'QUEUED', locked_until = ?, retry_count = retry_count + 1,
                    failures = failures + 1, error = ?, next_retry_at = ?, last_attempt_at = ?
                WHERE item_id = ? AND queue_name = ?
            ''', (next_retry_at, reason, next_retry_at, now, item_id, queue_name))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
