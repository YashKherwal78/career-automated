from typing import Any

class SchemaInspector:
    def __init__(self, adapter: Any):
        self.adapter = adapter

    def table_exists(self, table_name: str) -> bool:
        # Use a dialect-agnostic way to check if a table exists.
        # Actually, if we just try to SELECT 1 FROM table LIMIT 0, it throws if it doesn't exist.
        try:
            # We must handle both adapter and raw connection formats
            target = self.adapter if hasattr(self, 'adapter') else self
            if hasattr(target, 'execute'):
                cursor = target.execute(f"SELECT 1 FROM {table_name} LIMIT 0")
                return True
        except Exception:
            pass
        return False

    def column_exists(self, table_name: str, column_name: str) -> bool:
        try:
            cursor = self.adapter.execute(f"SELECT * FROM {table_name} LIMIT 0")
            columns = [col[0].lower() for col in cursor.description]
            return column_name.lower() in columns
        except Exception:
            return False

