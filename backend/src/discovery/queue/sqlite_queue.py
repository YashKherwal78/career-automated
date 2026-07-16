import sqlite3
import json
import time
import uuid
from typing import Any, Dict, Optional
from src.discovery.queue.base_queue import BaseQueue
from src.runtime.postgres.connection import get_connection, USE_POSTGRES
from src.runtime.redis.queue_manager import QueueManager
from src.runtime.redis.redis_client import RedisClient

class SQLiteQueue(BaseQueue):
    """
    Dual-Backend Queue implementation.
    Delegates to Redis (via QueueManager) in production/PostgreSQL mode,
    and falls back to SQLite in local/development mode.
    """
    
    def __init__(self, db_path: str = "data/crm.db"):
        self.db_path = db_path
        if not USE_POSTGRES:
            self._init_db()
        
    def _init_db(self):
        conn = get_connection()
        try:
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=NORMAL')
            conn.execute('PRAGMA busy_timeout=10000')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS local_queues (
                    item_id TEXT PRIMARY KEY,
                    queue_name TEXT NOT NULL,
                    payload JSON NOT NULL,
                    status TEXT DEFAULT 'QUEUED',
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
        item_id = str(uuid.uuid4())
        
        if USE_POSTGRES:
            # Redis Queue path
            wrapped = {
                "item_id": item_id,
                "payload": payload,
                "created_at": time.time(),
                "failures": 0,
                "retry_count": 0
            }
            QueueManager.enqueue(queue_name, wrapped)
            
            # Maintain active company set for duplicate filtering
            cid = payload.get("company_id")
            if cid:
                client = RedisClient.get_client()
                client.sadd(f"dedup:{queue_name}", str(cid))
                
            return item_id
            
        # SQLite Queue path
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
        if USE_POSTGRES:
            # Redis Queue path (blocking pop)
            wrapped = QueueManager.dequeue(queue_name, timeout=timeout or 5)
            if not wrapped:
                return None
            
            cid = wrapped["payload"].get("company_id")
            if cid:
                client = RedisClient.get_client()
                client.srem(f"dedup:{queue_name}", str(cid))
                
            # Temporarily cache under processing status in case of failure/nack
            client = RedisClient.get_client()
            client.set(f"processing:{queue_name}:{wrapped['item_id']}", json.dumps(wrapped), ex=300)
            
            return {
                "_item_id": wrapped["item_id"],
                "queue_name": queue_name,
                "payload": wrapped["payload"]
            }
            
        # SQLite Queue path
        now = time.time()
        lock_until = now + 300.0
        conn = get_connection()
        try:
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
            
            conn.execute('''
                UPDATE local_queues
                SET status = 'PROCESSING', locked_until = ?, last_attempt_at = ?
                WHERE item_id = ?
            ''', (lock_until, now, row["item_id"]))
            conn.commit()
            
            payload_val = row["payload"]
            parsed_payload = payload_val if isinstance(payload_val, dict) else json.loads(payload_val)
            
            return {
                "_item_id": row["item_id"],
                "queue_name": queue_name,
                "payload": parsed_payload
            }
        finally:
            conn.close()
            
    def ack(self, queue_name: str, item_id: str) -> bool:
        if USE_POSTGRES:
            # In Redis pop removes it automatically, so we just clean up the processing key
            client = RedisClient.get_client()
            return bool(client.delete(f"processing:{queue_name}:{item_id}"))
            
        # SQLite Queue path
        conn = get_connection()
        try:
            cursor = conn.execute('DELETE FROM local_queues WHERE item_id = ? AND queue_name = ?', (item_id, queue_name))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
            
    def nack(self, queue_name: str, item_id: str, reason: str = "", backoff_seconds: int = 3600) -> bool:
        if USE_POSTGRES:
            # Re-enqueue the processing item back to the Redis queue
            client = RedisClient.get_client()
            raw = client.get(f"processing:{queue_name}:{item_id}")
            if raw:
                wrapped = json.loads(raw)
                wrapped["failures"] += 1
                wrapped["retry_count"] += 1
                QueueManager.enqueue(queue_name, wrapped)
                client.delete(f"processing:{queue_name}:{item_id}")
                return True
            return False
            
        # SQLite Queue path
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

    def push_many(self, queue_name: str, payloads: list[Dict[str, Any]]) -> list[str]:
        if USE_POSTGRES:
            # Push multiple payloads using Redis dedup set filtering
            client = RedisClient.get_client()
            item_ids = []
            for p in payloads:
                cid = p.get("company_id")
                if cid and client.sismember(f"dedup:{queue_name}", str(cid)):
                    continue
                item_ids.append(self.push(queue_name, p))
            return item_ids
            
        # SQLite Queue path
        now = time.time()
        conn = get_connection()
        item_ids = []
        try:
            company_ids = [p.get("company_id") for p in payloads if p.get("company_id")]
            if not company_ids:
                return []
            
            placeholders = ",".join(["?"] * len(company_ids))
            existing_rows = conn.execute(
                f"SELECT json_extract(payload, '$.company_id') as cid FROM local_queues WHERE queue_name = ? AND status = 'QUEUED' AND json_extract(payload, '$.company_id') IN ({placeholders})",
                [queue_name] + company_ids
            ).fetchall()
            existing_cids = {dict(row)["cid"] for row in existing_rows if dict(row).get("cid")}

            rows_to_insert = []
            for p in payloads:
                cid = p.get("company_id")
                if cid and cid in existing_cids:
                    continue
                item_id = str(uuid.uuid4())
                item_ids.append(item_id)
                rows_to_insert.append((
                    item_id, queue_name, json.dumps(p), 'QUEUED', 0,
                    0, None, 0.0, 0.0, 0.0, now
                ))

            if rows_to_insert:
                cursor = conn.cursor()
                cursor.executemany('''
                    INSERT INTO local_queues (
                        item_id, queue_name, payload, status, failures,
                        retry_count, error, locked_until, next_retry_at, last_attempt_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', rows_to_insert)
                conn.commit()
        finally:
            conn.close()
        return item_ids
