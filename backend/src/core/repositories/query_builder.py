from typing import Any, List, Tuple

class QueryBuilder:
    """
    A lightweight query builder that prevents repositories from hardcoding
    SQL placeholders and syntax that varies between dialects.
    """
    
    def __init__(self, dialect: Any):
        self.dialect = dialect
        self.query = ""
        self.params = []

    def select(self, table: str, columns: List[str] = None) -> 'QueryBuilder':
        cols = ", ".join(self.dialect.quote_identifier(c) for c in columns) if columns else "*"
        self.query = f"SELECT {cols} FROM {self.dialect.quote_identifier(table)}"
        return self

    def where(self, conditions: List[Tuple[str, Any]]) -> 'QueryBuilder':
        if not conditions:
            return self
            
        clauses = []
        for col, val in conditions:
            clauses.append(f"{self.dialect.quote_identifier(col)} = {self.dialect.placeholder()}")
            if isinstance(val, bool):
                self.params.append(self.dialect.boolean(val))
            else:
                self.params.append(val)
                
        self.query += f" WHERE {' AND '.join(clauses)}"
        return self

    def limit(self, limit: int) -> 'QueryBuilder':
        self.query += f" {self.dialect.create_limit(limit)}"
        return self

    def order_by(self, column: str, desc: bool = False) -> 'QueryBuilder':
        direction = "DESC" if desc else "ASC"
        self.query += f" ORDER BY {self.dialect.quote_identifier(column)} {direction}"
        return self

    def build(self) -> Tuple[str, tuple]:
        return self.query, tuple(self.params)
