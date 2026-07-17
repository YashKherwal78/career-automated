from abc import ABC, abstractmethod
from typing import Any, Iterable, List, Optional

class DatabaseAdapter(ABC):
    def __init__(self, raw_conn: Any):
        self._conn = raw_conn

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()

    def cursor(self):
        return self._conn.cursor()

    def create_limit(self, limit: int) -> str:
        return f"LIMIT {limit}"

    @property
    def row_factory(self):
        return getattr(self._conn, 'row_factory', None)

    @property
    def dialect(self):
        return self

    @row_factory.setter
    def row_factory(self, value):
        self._conn.row_factory = value

    @abstractmethod
    def execute(self, query: str, params: Optional[Iterable[Any]] = None):
        pass

    @abstractmethod
    def executemany(self, query: str, seq_of_params: Iterable[Iterable[Any]]):
        pass

    @abstractmethod
    def placeholder(self) -> str:
        pass

    @abstractmethod
    def boolean(self, value: bool) -> Any:
        pass

    @abstractmethod
    def current_timestamp(self) -> str:
        pass

    @abstractmethod
    def quote_identifier(self, identifier: str) -> str:
        pass

    @abstractmethod
    def upsert(self, table: str, conflict_columns: List[str], update_columns: List[str]) -> str:
        pass


class SQLiteAdapter(DatabaseAdapter):
    def execute(self, query: str, params: Optional[Iterable[Any]] = None):
        if params is None:
            params = ()
        return self._conn.execute(query, params)

    def executemany(self, query: str, seq_of_params: Iterable[Iterable[Any]]):
        return self._conn.executemany(query, seq_of_params)

    def placeholder(self) -> str:
        return "?"

    def boolean(self, value: bool) -> Any:
        return 1 if value else 0

    def current_timestamp(self) -> str:
        return "CURRENT_TIMESTAMP"

    def quote_identifier(self, identifier: str) -> str:
        return f'"{identifier}"'

    def upsert(self, table: str, conflict_columns: List[str], update_columns: List[str]) -> str:
        conflict_str = ", ".join(self.quote_identifier(c) for c in conflict_columns)
        update_str = ", ".join([f"{self.quote_identifier(c)} = excluded.{self.quote_identifier(c)}" for c in update_columns])
        return f"ON CONFLICT({conflict_str}) DO UPDATE SET {update_str}"


class PostgreSQLAdapter(DatabaseAdapter):
    def execute(self, query: str, params: Optional[Iterable[Any]] = None):
        if params is None:
            params = ()
        # Postgres driver expects %s
        query = query.replace("?", "%s")
        return self._conn.execute(query, params)

    def executemany(self, query: str, seq_of_params: Iterable[Iterable[Any]]):
        query = query.replace("?", "%s")
        return self._conn.executemany(query, seq_of_params)

    def placeholder(self) -> str:
        return "%s"

    def boolean(self, value: bool) -> Any:
        return True if value else False

    def current_timestamp(self) -> str:
        return "CURRENT_TIMESTAMP"

    def quote_identifier(self, identifier: str) -> str:
        return f'"{identifier}"'

    def upsert(self, table: str, conflict_columns: List[str], update_columns: List[str]) -> str:
        conflict_str = ", ".join(self.quote_identifier(c) for c in conflict_columns)
        update_str = ", ".join([f"{self.quote_identifier(c)} = EXCLUDED.{self.quote_identifier(c)}" for c in update_columns])
        return f"ON CONFLICT({conflict_str}) DO UPDATE SET {update_str}"
