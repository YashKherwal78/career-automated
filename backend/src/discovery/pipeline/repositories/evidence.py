import json
import uuid
import sqlite3
import zstandard as zstd
from typing import Optional, List, Dict, Any
from src.discovery.pipeline.repositories.base import BaseRepository

class EvidenceRepository(BaseRepository):
    def _init_db(self):
        from src.api.db import is_postgres
        with self.get_connection() as conn:
            if is_postgres():
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS crawl_evidence (
                        id TEXT PRIMARY KEY,
                        crawl_id TEXT NOT NULL,
                        board_id TEXT NOT NULL,
                        provider TEXT NOT NULL,
                        evidence_category TEXT NOT NULL,
                        reasons TEXT, 
                        evidence_score INTEGER NOT NULL,
                        schema_hash TEXT,
                        endpoint_family TEXT,
                        expires_at REAL, 
                        compression TEXT DEFAULT 'zstd',
                        payload_blob BYTEA
                    )
                """)
            else:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS crawl_evidence (
                        id TEXT PRIMARY KEY,
                        crawl_id TEXT NOT NULL,
                        board_id TEXT NOT NULL,
                        provider TEXT NOT NULL,
                        evidence_category TEXT NOT NULL,
                        reasons TEXT, 
                        evidence_score INTEGER NOT NULL,
                        schema_hash TEXT,
                        endpoint_family TEXT,
                        expires_at REAL, 
                        compression TEXT DEFAULT 'zstd',
                        payload_blob BLOB
                    )
                """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_provider_hash ON crawl_evidence(provider, schema_hash)")
            conn.commit()

    def _compress(self, payload: dict | bytes) -> bytes:
        if isinstance(payload, bytes):
            payload_bytes = payload
        else:
            payload_bytes = json.dumps(payload).encode('utf-8')
            
        cctx = zstd.ZstdCompressor(level=3)
        return cctx.compress(payload_bytes)

    def _decompress(self, blob: bytes) -> dict:
        dctx = zstd.ZstdDecompressor()
        decompressed = dctx.decompress(blob)
        return json.loads(decompressed.decode('utf-8'))

    def save_evidence(self, crawl_id: str, board_id: str, provider: str, category: str, reasons: str, score: int, schema_hash: str, endpoint_family: str, expires_at: float, payload: dict | bytes) -> str:
        compressed = self._compress(payload)
        evidence_id = str(uuid.uuid4())
        
        from src.api.db import is_postgres
        with self.get_connection() as conn:
            is_sqlite = getattr(conn, "_is_sqlite", isinstance(conn, sqlite3.Connection))
            query = """
                INSERT INTO crawl_evidence (
                    id, crawl_id, board_id, provider, evidence_category, reasons, evidence_score, schema_hash, endpoint_family, expires_at, compression, payload_blob
                ) VALUES ({}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {})
            """
            if not is_sqlite and is_postgres():
                query = query.format("%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s")
            else:
                query = query.format("?", "?", "?", "?", "?", "?", "?", "?", "?", "?", "?", "?")
                
            conn.execute(query, (evidence_id, crawl_id, board_id, provider, category, reasons, score, schema_hash, endpoint_family, expires_at, "zstd", compressed))
            conn.commit()
            
        return evidence_id
        
    def get_reference_payloads(self, provider: str) -> List[Dict[str, Any]]:
        from src.api.db import is_postgres
        with self.get_connection() as conn:
            if not is_postgres():
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT schema_hash, payload_blob FROM crawl_evidence WHERE provider = ? AND evidence_category = 'REFERENCE'", (provider,))
                rows = cursor.fetchall()
            else:
                cursor = conn.execute("SELECT schema_hash, payload_blob FROM crawl_evidence WHERE provider = %s AND evidence_category = 'REFERENCE'", (provider,))
                rows = cursor.fetchall()
                
            results = []
            for row in rows:
                if isinstance(row, dict) or isinstance(row, sqlite3.Row):
                    blob = row['payload_blob']
                    h = row['schema_hash']
                else:
                    h = row[0]
                    blob = row[1]
                    
                if isinstance(blob, memoryview):
                    blob = blob.tobytes()
                    
                results.append({
                    "schema_hash": h,
                    "payload": self._decompress(blob)
                })
                
            return results
