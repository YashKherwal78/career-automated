from src.discovery.pipeline.repositories.base import BaseRepository

class SyncRepository(BaseRepository):
    def _init_db(self):
        from src.api.db import is_postgres
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
        from src.api.db import is_postgres
        with self.get_connection() as conn:
            if is_postgres():
                conn.execute("""
                    INSERT INTO board_syncs (
                        id, board_id, snapshot_id, started_at, finished_at, duration_ms,
                        http_status, bytes_downloaded, jobs_extracted, jobs_inserted,
                        jobs_updated, jobs_archived, success, error_message
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )
                """, (
                    sync_data['id'], sync_data['board_id'], sync_data.get('snapshot_id'),
                    sync_data['started_at'], sync_data['finished_at'], sync_data['duration_ms'],
                    sync_data.get('http_status'), sync_data.get('bytes_downloaded'),
                    sync_data.get('jobs_extracted'), sync_data.get('jobs_inserted'),
                    sync_data.get('jobs_updated'), sync_data.get('jobs_archived'),
                    sync_data.get('success'), sync_data.get('error_message')
                ))
            else:
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
