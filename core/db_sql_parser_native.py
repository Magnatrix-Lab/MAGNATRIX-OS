"""DB SQL Parser -- Lexer, parser, AST builder for SQL."""
from dataclasses import dataclass
from pathlib import Path
import json
import re

@dataclass
class SQLAST:
    query_type: str = ""
    table: str = ""
    columns: list[str] = None
    values: list[dict] = None
    conditions: list[dict] = None
    order_by: list[str] = None
    limit: int = 0
    raw: str = ""

    def __post_init__(self):
        if self.columns is None:
            self.columns = []
        if self.values is None:
            self.values = []
        if self.conditions is None:
            self.conditions = []
        if self.order_by is None:
            self.order_by = []

class DBSQLParser:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._queries: list[SQLAST] = []
        self._persist_path = self.root / "db_sql_parser.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._queries = [SQLAST(**q) for q in data.get("queries", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "queries": [q.__dict__ for q in self._queries]
        }, indent=2))

    def parse(self, sql: str) -> SQLAST:
        ast = SQLAST(raw=sql)
        sql = sql.strip().upper()

        if sql.startswith("SELECT"):
            ast.query_type = "SELECT"
            m = re.search(r"FROM\s+(\w+)", sql, re.I)
            if m:
                ast.table = m.group(1)
            cols = re.search(r"SELECT\s+(.*?)\s+FROM", sql, re.I)
            if cols:
                ast.columns = [c.strip() for c in cols.group(1).split(",")]
            limit = re.search(r"LIMIT\s+(\d+)", sql, re.I)
            if limit:
                ast.limit = int(limit.group(1))
        elif sql.startswith("INSERT"):
            ast.query_type = "INSERT"
            m = re.search(r"INTO\s+(\w+)", sql, re.I)
            if m:
                ast.table = m.group(1)
        elif sql.startswith("UPDATE"):
            ast.query_type = "UPDATE"
            m = re.search(r"UPDATE\s+(\w+)", sql, re.I)
            if m:
                ast.table = m.group(1)
        elif sql.startswith("DELETE"):
            ast.query_type = "DELETE"
            m = re.search(r"FROM\s+(\w+)", sql, re.I)
            if m:
                ast.table = m.group(1)
        elif sql.startswith("CREATE"):
            ast.query_type = "CREATE"
            m = re.search(r"TABLE\s+(\w+)", sql, re.I)
            if m:
                ast.table = m.group(1)

        self._queries.append(ast)
        self._save()
        return ast

    def to_dict(self) -> dict:
        return {"query_count": len(self._queries)}

    def get_stats(self) -> dict:
        by_type = {}
        for q in self._queries:
            by_type[q.query_type] = by_type.get(q.query_type, 0) + 1
        return {"queries": len(self._queries), "by_type": by_type}

__all__ = ["DBSQLParser", "SQLAST"]
