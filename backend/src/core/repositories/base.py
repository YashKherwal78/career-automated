from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any
from src.api.db import get_connection
from src.core.repositories.adapter import DatabaseAdapter, PostgreSQLAdapter, SQLiteAdapter
from src.core.repositories.schema_inspector import SchemaInspector

_active_transaction = ContextVar('_active_transaction', default=None)

class _TxConnectionWrapper:
    def __init__(self, conn):
        self._conn = conn
    def __getattr__(self, name):
        return getattr(self._conn, name)
    def close(self):
        pass
    def commit(self):
        pass
    def rollback(self):
        pass

class BaseRepository:
    def __init__(self, db_path: str = "boards.db"):
        self.db_path = db_path
        
    def _create_adapter(self, conn: Any) -> DatabaseAdapter:
        if not getattr(conn, "_is_sqlite", True):
            return PostgreSQLAdapter(conn)
        return SQLiteAdapter(conn)

        
    def get_connection(self) -> DatabaseAdapter:
        tx = _active_transaction.get()
        if tx is not None:
            return self._create_adapter(_TxConnectionWrapper(tx))
        return self._create_adapter(get_connection())
        
    @property
    def schema(self) -> SchemaInspector:
        return SchemaInspector(self.get_connection())
        
    @contextmanager
    def transaction(self):
        # If we already have an active transaction, just yield the adapter
        existing_tx = _active_transaction.get()
        if existing_tx is not None:
            yield self._create_adapter(existing_tx)
            return

        conn = get_connection()
        token = _active_transaction.set(conn)
        try:
            yield self._create_adapter(conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            _active_transaction.reset(token)
            conn.close()
