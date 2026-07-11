from src.discovery.pipeline.repositories.base import BaseRepository

class SyncRepository(BaseRepository):
    def _init_db(self):
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS board_syncs (
                    id TEXT PRIMARY KEY,
                    board_id TEXT,
                    snapshot_id TEXT,
                    started_at REAL,
                    finished_at REAL,
                    duration_ms REAL,
                    http_status INTEGER,
                    bytes_downloaded INTEGER,
                    jobs_extracted INTEGER,
                    jobs_inserted INTEGER,
                    jobs_updated INTEGER,
                    jobs_archived INTEGER,
                    success BOOLEAN,
                    error_message TEXT
                )
            """)
            conn.commit()

    def record_sync(self, sync_data: dict):
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO board_syncs (
                    id, board_id, snapshot_id, started_at, finished_at, duration_ms,
                    http_status, bytes_downloaded, jobs_extracted, jobs_inserted,
                    jobs_updated, jobs_archived, success, error_message
                ) VALUES (
                    :id, :board_id, :snapshot_id, :started_at, :finished_at, :duration_ms,
                    :http_status, :bytes_downloaded, :jobs_extracted, :jobs_inserted,
                    :jobs_updated, :jobs_archived, :success, :error_message
                )
            """, sync_data)
            conn.commit()
