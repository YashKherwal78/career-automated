from typing import Optional, Any, List, Dict
from src.core.repositories.interfaces import IProviderRepository
from src.core.repositories.base import BaseRepository

class ProviderRepository(BaseRepository, IProviderRepository):
    def get_active_providers(self, tx: Optional[Any] = None) -> List[Dict[str, Any]]:
        conn = tx if tx else self.get_connection()
        try:
            # We assume boolean true is handled gracefully by sqlite when compared against 1
            cur = conn.execute("SELECT * FROM providers WHERE enabled=1 OR enabled=TRUE")
            return [dict(row) if hasattr(row, 'keys') else dict(zip([col[0] for col in cur.description], row)) for row in cur.fetchall()]
        finally:
            if not tx:
                conn.close()
                
    def get_provider(self, provider_id: str, tx: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        conn = tx if tx else self.get_connection()
        try:
            p = conn.dialect.placeholder()
            cur = conn.execute(f"SELECT * FROM providers WHERE id={p}", (provider_id,))
            row = cur.fetchone()
            if row:
                return dict(row) if hasattr(row, 'keys') else dict(zip([col[0] for col in cur.description], row))
            return None
        finally:
            if not tx:
                conn.close()
                
    def update_worker_count(self, provider_id: str, current_workers: int, tx: Optional[Any] = None) -> None:
        conn = tx if tx else self.get_connection()
        try:
            p = conn.dialect.placeholder()
            conn.execute(f"UPDATE providers SET current_workers={p} WHERE id={p}", (current_workers, provider_id))
            if not tx:
                conn.commit()
        finally:
            if not tx:
                conn.close()

