from typing import Optional, Any, Dict
from src.core.repositories.interfaces import ISessionRepository
from src.core.repositories.base import BaseRepository

class SessionRepository(BaseRepository, ISessionRepository):
    def create_session(self, session_id: str, provider: str, tx: Optional[Any] = None) -> None:
        conn = tx if tx else self.get_connection()
        try:
            p = conn.dialect.placeholder()
            conn.execute(f"INSERT INTO crawl_sessions (session_id, provider) VALUES ({p}, {p})", (session_id, provider))
            if not tx:
                conn.commit()
        finally:
            if not tx:
                conn.close()
                
    def stop_session(self, session_id: str, tx: Optional[Any] = None) -> None:
        conn = tx if tx else self.get_connection()
        try:
            p = conn.dialect.placeholder()
            now = conn.dialect.current_timestamp()
            conn.execute(f"UPDATE crawl_sessions SET status='STOPPED', ended_at={now} WHERE session_id={p}", (session_id,))
            if not tx:
                conn.commit()
        finally:
            if not tx:
                conn.close()
                
    def record_metrics(self, session_id: str, provider: str, metrics: Dict[str, Any], tx: Optional[Any] = None) -> None:
        conn = tx if tx else self.get_connection()
        try:
            p = conn.dialect.placeholder()
            updates = []
            values = []
            for key, val in metrics.items():
                updates.append(f"{key}={key}+{p}")
                values.append(val)
                
            if updates:
                query = f"UPDATE crawl_sessions SET {', '.join(updates)} WHERE session_id={p} AND provider={p}"
                values.extend([session_id, provider])
                conn.execute(query, tuple(values))
                if not tx:
                    conn.commit()
        finally:
            if not tx:
                conn.close()

