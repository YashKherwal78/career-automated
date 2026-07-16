from pathlib import Path
from src.runtime.config.settings import Settings
from src.runtime.postgres.connection import (
    CompatConnection,
    CompatCursor,
    get_connection,
    USE_POSTGRES
)
from typing import Any

DATABASE_PATH = str(Path(__file__).resolve().parents[2] / "data" / "crm.db")
DATABASE_URL = Settings.DATABASE_URL

# Maintain helpers used by API
def is_postgres() -> bool:
    return USE_POSTGRES


def json_extract(column: str, path: str) -> str:
    if USE_POSTGRES:
        if path.startswith("$."):
            return f"({column})::jsonb ->> '{path[2:]}'"
        return f"({column})::jsonb ->> '{path}'"
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
