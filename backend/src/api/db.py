import os
import sqlite3
from typing import Optional, Iterable, Any
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "")
DATABASE_PATH = os.getenv("DATABASE_PATH", str(Path(__file__).resolve().parents[2] / "data" / "crm.db"))
USE_POSTGRES = bool(DATABASE_URL)

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError as e:  # pragma: no cover
    import logging
    logging.error(f"Failed to import psycopg: {e}")
    psycopg = None
    dict_row = None


class CompatCursor:
    def __init__(self, conn: Any, is_sqlite: bool, row_factory: Optional[Any] = None):
        self._conn = conn
        self._is_sqlite = is_sqlite
        self._row_factory = row_factory
        self._cursor = self._open_cursor()

    def _open_cursor(self):
        if self._is_sqlite:
            cursor = self._conn.cursor()
            if self._row_factory is not None:
                cursor.row_factory = self._row_factory
            return cursor

        if self._row_factory is sqlite3.Row and dict_row is not None:
            return self._conn.cursor(row_factory=dict_row)
        return self._conn.cursor()

    def execute(self, query: str, params: Optional[Iterable[Any]] = None):
        if params is None:
            params = ()
        if not self._is_sqlite:
            query = query.replace("?", "%s")
        return self._cursor.execute(query, params)

    def executemany(self, query: str, seq_of_params: Iterable[Iterable[Any]]):
        if not self._is_sqlite:
            query = query.replace("?", "%s")
        return self._cursor.executemany(query, seq_of_params)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchmany(self, size: Optional[int] = None):
        return self._cursor.fetchmany(size)

    def __getattr__(self, name: str):
        return getattr(self._cursor, name)

    def __iter__(self):
        return iter(self._cursor)

    @property
    def row_factory(self):
        return self._row_factory

    @row_factory.setter
    def row_factory(self, value: Optional[Any]):
        self._row_factory = value
        self._cursor = self._open_cursor()


class CompatConnection:
    def __init__(self, conn: Any, is_sqlite: bool):
        self._conn = conn
        self._is_sqlite = is_sqlite
        self.row_factory = sqlite3.Row

    def cursor(self):
        return CompatCursor(self._conn, self._is_sqlite, row_factory=self.row_factory)

    def execute(self, query: str, params: Optional[Iterable[Any]] = None):
        cursor = self.cursor()
        cursor.execute(query, params)
        return cursor

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def __getattr__(self, name: str):
        return getattr(self._conn, name)


def is_postgres() -> bool:
    return USE_POSTGRES


def json_extract(column: str, path: str) -> str:
    if USE_POSTGRES:
        if path.startswith("$."):
            return f"{column} ->> '{path[2:]}'"
        return f"{column} ->> '{path}'"
    return f"json_extract({column}, '{path}')"


def table_exists(conn: Any, table_name: str) -> bool:
    cursor = conn.cursor()
    if USE_POSTGRES:
        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s)",
            (table_name,),
        )
        return bool(cursor.fetchone()[0])

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None


def get_connection() -> CompatConnection:
    print(f"DEBUG: get_connection called. USE_POSTGRES={USE_POSTGRES}, DATABASE_URL={DATABASE_URL}", flush=True)
    if USE_POSTGRES:
        if psycopg is None:
            raise RuntimeError("DATABASE_URL is set but psycopg is not installed. Install psycopg[binary].")
        print("DEBUG: Calling psycopg.connect...", flush=True)
        try:
            raw_conn = psycopg.connect(DATABASE_URL, autocommit=True, prepare_threshold=None)
            print("DEBUG: psycopg.connect succeeded.", flush=True)
        except Exception as e:
            print(f"DEBUG: psycopg.connect failed: {e}", flush=True)
            raise
        return CompatConnection(raw_conn, is_sqlite=False)

    print("DEBUG: Falling back to sqlite3", flush=True)
    raw_conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30.0)
    raw_conn.row_factory = sqlite3.Row
    return CompatConnection(raw_conn, is_sqlite=True)
