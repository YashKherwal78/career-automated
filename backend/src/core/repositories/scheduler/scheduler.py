from typing import Optional, Any, Dict
from src.core.repositories.interfaces import ISchedulerRepository, SchedulerState
from src.core.repositories.base import BaseRepository

class SchedulerRepository(BaseRepository, ISchedulerRepository):
    def update_state(self, state: SchedulerState, version: str, pid: int, host: str, tx: Optional[Any] = None) -> None:
        conn = tx if tx else self.get_connection()
        try:
            p = conn.dialect.placeholder()
            now = conn.dialect.current_timestamp()
            upsert = conn.dialect.upsert(
                table="scheduler_state",
                conflict_columns=["id"],
                update_columns=["state", "version", "pid", "host", "heartbeat"]
            )
            
            conn.execute(f"""
                INSERT INTO scheduler_state (id, state, version, started_at, pid, host, heartbeat)
                VALUES (1, {p}, {p}, {now}, {p}, {p}, {now})
                {upsert}
            """, (state.value, version, pid, host))
            if not tx:
                conn.commit()
        finally:
            if not tx:
                conn.close()
                
    def heartbeat(self, tx: Optional[Any] = None) -> None:
        conn = tx if tx else self.get_connection()
        try:
            now = conn.dialect.current_timestamp()
            conn.execute(f"UPDATE scheduler_state SET heartbeat={now} WHERE id=1")
            if not tx:
                conn.commit()
        finally:
            if not tx:
                conn.close()
                
    def get_state(self, tx: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        conn = tx if tx else self.get_connection()
        try:
            cur = conn.execute("SELECT * FROM scheduler_state WHERE id=1")
            row = cur.fetchone()
            if row:
                return dict(row) if hasattr(row, 'keys') else dict(zip([col[0] for col in cur.description], row))
            return None
        finally:
            if not tx:
                conn.close()
