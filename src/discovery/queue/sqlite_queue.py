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
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS local_queues (
                    item_id TEXT PRIMARY KEY,
                    queue_name TEXT NOT NULL,
                    payload JSON NOT NULL,
                    status TEXT DEFAULT 'QUEUED', -- QUEUED, PROCESSING, DEAD
                    locked_until INTEGER DEFAULT 0,
                    created_at INTEGER
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_local_queues ON local_queues(queue_name, status, locked_until)')
            
    def push(self, queue_name: str, payload: Dict[str, Any]) -> str:
        import uuid
        item_id = str(uuid.uuid4())
        created_at = int(time.time())
        
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.execute('''
                INSERT INTO local_queues (item_id, queue_name, payload, created_at)
                VALUES (?, ?, ?, ?)
            ''', (item_id, queue_name, json.dumps(payload), created_at))
        return item_id
        
    def pop(self, queue_name: str, timeout: int = 0) -> Optional[Dict[str, Any]]:
        """
        Pops an item and locks it for 300 seconds.
        """
        now = int(time.time())
        lock_until = now + 300 # 5 minute lock
        
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            # Find the oldest available item
            cursor = conn.execute('''
                SELECT item_id, payload FROM local_queues 
                WHERE queue_name = ? AND status = 'QUEUED' AND locked_until <= ?
                ORDER BY created_at ASC LIMIT 1
            ''', (queue_name, now))
            
            row = cursor.fetchone()
            if not row:
                return None
                
            item_id, payload_str = row
            
            # Lock it
            conn.execute('''
                UPDATE local_queues SET status = 'PROCESSING', locked_until = ?
                WHERE item_id = ?
            ''', (lock_until, item_id))
            
            return {"_item_id": item_id, "payload": json.loads(payload_str)}
            
    def ack(self, queue_name: str, item_id: str) -> bool:
        """Deletes the item from the queue."""
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.execute('DELETE FROM local_queues WHERE item_id = ? AND queue_name = ?', (item_id, queue_name))
            return cursor.rowcount > 0
            
    def nack(self, queue_name: str, item_id: str, reason: str = "") -> bool:
        """Unlocks the item so it can be retried, applying a 1-hour backoff."""
        lock_until = int(time.time()) + 3600
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.execute('''
                UPDATE local_queues SET status = 'QUEUED', locked_until = ?
                WHERE item_id = ? AND queue_name = ?
            ''', (lock_until, item_id, queue_name))
            return cursor.rowcount > 0
