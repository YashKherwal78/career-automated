import sqlite3
import time
from src.discovery.pipeline.repositories.base import BaseRepository
from typing import Optional, Tuple, Dict, Any

class SyncRepository(BaseRepository):
    def _init_db(self):
        # Migrations are now handled in 025_evidence_system.sql
        pass

    def get_board_statistics(self, board_id: str) -> Tuple[float, int]:
        """Returns (rolling_mean, rolling_count)"""
        from src.api.db import is_postgres
        with self.get_connection() as conn:
            if not is_postgres():
                cursor = conn.execute("SELECT rolling_mean, rolling_count FROM board_statistics WHERE board_id = ?", (board_id,))
            else:
                cursor = conn.execute("SELECT rolling_mean, rolling_count FROM board_statistics WHERE board_id = %s", (board_id,))
            row = cursor.fetchone()
            if row:
                if isinstance(row, dict) or isinstance(row, sqlite3.Row):
                    return row['rolling_mean'], row['rolling_count']
                return row[0], row[1]
            return 0.0, 0

    def record_sync(self, sync_data: dict, outcome: str):
        from src.api.db import is_postgres
        now = time.time()
        
        with self.get_connection() as conn:
            is_sqlite = getattr(conn, "_is_sqlite", isinstance(conn, sqlite3.Connection))
            
            # 1. Update Board Statistics
            jobs_extracted = sync_data.get('jobs_extracted', 0)
            if outcome == "SUCCESS":
                board_id = sync_data['board_id']
                if not is_sqlite and is_postgres():
                    conn.execute("""
                        INSERT INTO board_statistics (board_id, rolling_mean, rolling_count, last_updated)
                        VALUES (%s, %s, 1, %s)
                        ON CONFLICT (board_id) DO UPDATE SET
                        rolling_mean = (board_statistics.rolling_mean * board_statistics.rolling_count + EXCLUDED.rolling_mean) / (board_statistics.rolling_count + 1),
                        rolling_count = board_statistics.rolling_count + 1,
                        last_updated = EXCLUDED.last_updated
                    """, (board_id, jobs_extracted, now))
                else:
                    # SQLite upsert
                    conn.execute("""
                        INSERT INTO board_statistics (board_id, rolling_mean, rolling_count, last_updated)
                        VALUES (?, ?, 1, ?)
                        ON CONFLICT(board_id) DO UPDATE SET
                        rolling_mean = (board_statistics.rolling_mean * board_statistics.rolling_count + excluded.rolling_mean) / (board_statistics.rolling_count + 1),
                        rolling_count = board_statistics.rolling_count + 1,
                        last_updated = excluded.last_updated
                    """, (board_id, jobs_extracted, now))

            # 2. Insert Metadata
            meta_query = """
                INSERT INTO crawl_metadata (
                    crawl_id, board_id, provider, connector_name, started_at, duration_ms,
                    http_status, content_length, schema_hash, connector_version_id,
                    jobs_extracted, jobs_inserted
                ) VALUES ({}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {})
            """
            if not is_sqlite and is_postgres():
                meta_query = meta_query.format("%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s")
            else:
                meta_query = meta_query.format("?", "?", "?", "?", "?", "?", "?", "?", "?", "?", "?", "?")

            conn.execute(meta_query, (
                sync_data['id'], sync_data['board_id'], sync_data.get('provider', 'unknown'),
                sync_data.get('connector_name', 'unknown'), sync_data['started_at'], sync_data['duration_ms'],
                sync_data.get('http_status'), sync_data.get('bytes_downloaded'),
                sync_data.get('schema_hash'), sync_data.get('connector_version_id', 'unknown'),
                jobs_extracted, sync_data.get('jobs_inserted', 0)
            ))

            # 3. Insert Outcome
            outcome_query = """
                INSERT INTO crawl_outcome (crawl_id, provider, classification)
                VALUES ({}, {}, {})
            """
            if not is_sqlite and is_postgres():
                outcome_query = outcome_query.format("%s", "%s", "%s")
            else:
                outcome_query = outcome_query.format("?", "?", "?")
                
            conn.execute(outcome_query, (
                sync_data['id'], sync_data.get('provider', 'unknown'), outcome
            ))
            
            conn.commit()
