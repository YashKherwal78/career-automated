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
        return sqlite3.connect(self.db_path)
