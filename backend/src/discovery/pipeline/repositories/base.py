import sqlite3
from typing import Optional

class BaseRepository:
    def __init__(self, db_path: str = "boards.db"):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """Override in subclasses to create schema."""
        pass
        
    def get_connection(self):
        from src.api.db import get_connection, is_postgres
        if is_postgres():
            try:
                return get_connection()
            except Exception:
                pass
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=10000;")
        conn.row_factory = sqlite3.Row
        return conn

