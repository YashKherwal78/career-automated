from typing import List, Tuple
from src.core.repositories.base import BaseRepository

class CleanupRepository(BaseRepository):
    def clean_old_snapshots(self, seven_days_ago: float) -> int:
        with self.transaction() as conn:
            if self.schema.table_exists("board_snapshots"):
                p = conn.dialect.placeholder()
                c_del = conn.execute(f"DELETE FROM board_snapshots WHERE synced_at < {p}", (seven_days_ago,))
                return c_del.rowcount
            return 0

    def get_failed_endpoints(self) -> List[str]:
        with self.transaction() as conn:
            if self.schema.table_exists("career_endpoints"):
                limit = conn.dialect.create_limit(20)
                cursor_f = conn.execute(f"SELECT company_id FROM career_endpoints WHERE status = 'FAILED' {limit}")
                return [row["company_id"] if hasattr(row, 'keys') else row[0] for row in cursor_f.fetchall()]
            return []

    def is_in_discovery_queue(self, company_id: str) -> bool:
        from backend.src.runtime.postgres.connection import USE_POSTGRES
        if USE_POSTGRES:
            from backend.src.runtime.redis.redis_client import RedisClient
            client = RedisClient.get_client()
            return bool(client.sismember("dedup:discovery_queue", str(company_id)))

        from src.api.db import json_extract
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            json_col = json_extract('payload', '$.company_id')
            cursor_q = conn.execute(f'''
                SELECT 1 FROM local_queues 
                WHERE queue_name = 'discovery_queue' AND {json_col} = {p}
            ''', (company_id,))
            return cursor_q.fetchone() is not None

    def recover_stuck_queues(self, now: float) -> int:
        from backend.src.runtime.postgres.connection import USE_POSTGRES
        if USE_POSTGRES:
            # Redis TTL handles processing keys cleanup automatically
            return 0

        count = 0
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            cursor = conn.execute(f'''
                SELECT item_id, queue_name FROM local_queues
                WHERE status = 'PROCESSING' AND locked_until <= {p}
            ''', (now,))
            
            stuck_items = cursor.fetchall()
            for row in stuck_items:
                item_id, _ = row
                conn.execute(f'''
                    UPDATE local_queues
                    SET status = 'QUEUED', locked_until = 0.0
                    WHERE item_id = {p}
                ''', (item_id,))
                count += 1
        return count

    def optimize_database(self, should_vacuum: bool) -> None:
        conn = self.get_connection()
        try:
            # Check the dialect name directly to execute appropriate vacuum syntax.
            # Usually VACUUM ANALYZE for Postgres, ANALYZE for SQLite.
            if type(conn.dialect).__name__ == "PostgreSQLAdapter":
                conn.execute("VACUUM ANALYZE")
            else:
                conn.execute("ANALYZE")
                if should_vacuum:
                    conn.execute("VACUUM")
            conn.commit()
        finally:
            conn.close()

