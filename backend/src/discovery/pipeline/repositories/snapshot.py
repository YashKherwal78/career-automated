import gzip
import json
import hashlib
import uuid
import sqlite3
from typing import Optional
from src.discovery.pipeline.repositories.base import BaseRepository

class SnapshotRepository(BaseRepository):
    def _init_db(self):
        from src.api.db import is_postgres
        with self.get_connection() as conn:
            if is_postgres():
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS board_snapshots (
                        id TEXT PRIMARY KEY,
                        board_id TEXT,
                        synced_at REAL,
                        content_sha256 TEXT,
                        size_bytes INTEGER,
                        compression TEXT,
                        payload_blob BYTEA
                    )
                """)
            else:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS board_snapshots (
                        id TEXT PRIMARY KEY,
                        board_id TEXT,
                        synced_at REAL,
                        content_sha256 TEXT,
                        size_bytes INTEGER,
                        compression TEXT,
                        payload_blob BLOB
                    )
                """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_board ON board_snapshots(board_id)")
            conn.commit()

    def save(self, board_id: str, raw_payload: dict, synced_at: float) -> str:
        payload_bytes = json.dumps(raw_payload).encode('utf-8')
        compressed = gzip.compress(payload_bytes)
        content_sha256 = hashlib.sha256(payload_bytes).hexdigest()
        size_bytes = len(payload_bytes)
        snapshot_id = str(uuid.uuid4())
        
        from src.api.db import is_postgres
        with self.get_connection() as conn:
            if is_postgres():
                conn.execute("""
                    INSERT INTO board_snapshots (
                        id, board_id, synced_at, content_sha256, size_bytes, compression, payload_blob
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (snapshot_id, board_id, synced_at, content_sha256, size_bytes, "gzip", compressed))
            else:
                conn.execute("""
                    INSERT INTO board_snapshots (
                        id, board_id, synced_at, content_sha256, size_bytes, compression, payload_blob
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (snapshot_id, board_id, synced_at, content_sha256, size_bytes, "gzip", compressed))
            conn.commit()
            
        return snapshot_id
        
    def get(self, snapshot_id: str) -> Optional[dict]:
        from src.api.db import is_postgres
        with self.get_connection() as conn:
            if not is_postgres():
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT payload_blob, compression FROM board_snapshots WHERE id = ?", (snapshot_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                blob = row['payload_blob']
                compression = row['compression']
            else:
                cursor = conn.execute("SELECT payload_blob, compression FROM board_snapshots WHERE id = %s", (snapshot_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                if isinstance(row, dict):
                    blob = row['payload_blob']
                    compression = row['compression']
                else:
                    blob = row[0]
                    compression = row[1]
                    
            if compression == 'gzip':
                # Postgres psycopg may return memoryview for bytea
                if isinstance(blob, memoryview):
                    blob = blob.tobytes()
                blob = gzip.decompress(blob)
            return json.loads(blob.decode('utf-8'))
