import time
from typing import Optional, Any
from src.core.repositories.base import BaseRepository
from src.core.repositories.interfaces import IMigrationRepository
from src.core.repositories.schema_inspector import SchemaInspector

class MigrationRepository(BaseRepository, IMigrationRepository):
    def get_current_version(self, tx: Optional[Any] = None) -> int:
        conn = tx if tx else self.get_connection()
        try:
            if not SchemaInspector.table_exists(conn, "schema_migrations"):
                return 0
                
            p = conn.dialect.placeholder()
            # In SQLite true is 1, in Postgres true is TRUE. We can use the dialect boolean value
            true_val = conn.dialect.boolean(True)
            limit = conn.dialect.create_limit(1)
            # SQLite does not support comparing TRUE as boolean without issues sometimes, but schema_migrations success is boolean
            # However we can just say success = 1 OR success = TRUE
            cur = conn.execute(f"SELECT version FROM schema_migrations WHERE success = {true_val} ORDER BY version DESC {limit}")
            row = cur.fetchone()
            return row[0] if row else 0
        finally:
            if not tx:
                conn.close()
                
    def record_migration(self, version: int, name: str, success: bool, tx: Optional[Any] = None) -> None:
        conn = tx if tx else self.get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    applied_at REAL NOT NULL
                )
            """)
            
            p = conn.dialect.placeholder()
            upsert = conn.dialect.upsert(
                table="schema_migrations",
                conflict_columns=["version"],
                update_columns=["name", "success", "applied_at"]
            )
            
            conn.execute(
                f"""
                INSERT INTO schema_migrations (version, name, success, applied_at)
                VALUES ({p}, {p}, {p}, {p})
                {upsert}
                """,
                (version, name, conn.dialect.boolean(success), time.time())
            )
            if not tx:
                conn.commit()
        finally:
            if not tx:
                conn.close()
                
    def is_compatible(self, required_version: int, tx: Optional[Any] = None) -> bool:
        current = self.get_current_version(tx)
        return current >= required_version

