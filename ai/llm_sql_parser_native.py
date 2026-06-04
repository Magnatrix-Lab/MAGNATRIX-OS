"""SQL Parser - SQL statement parser for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import re

class SQLType(Enum):
    SELECT = auto(); INSERT = auto(); UPDATE = auto(); DELETE = auto(); CREATE = auto()

@dataclass
class SQLParser:

    def parse(self, sql: str) -> Dict:
        sql = sql.strip().upper()
        if sql.startswith("SELECT"):
            return {"type": SQLType.SELECT, "columns": self._extract_columns(sql), "table": self._extract_table(sql)}
        elif sql.startswith("INSERT"):
            return {"type": SQLType.INSERT, "table": self._extract_table(sql), "values": self._extract_values(sql)}
        elif sql.startswith("UPDATE"):
            return {"type": SQLType.UPDATE, "table": self._extract_table(sql), "set": self._extract_set(sql)}
        elif sql.startswith("DELETE"):
            return {"type": SQLType.DELETE, "table": self._extract_table(sql)}
        elif sql.startswith("CREATE"):
            return {"type": SQLType.CREATE, "table": self._extract_table(sql)}
        return {"type": None}

    def _extract_columns(self, sql: str) -> List[str]:
        m = re.search(r"SELECT\s+(.*?)\s+FROM", sql, re.IGNORECASE)
        return [c.strip() for c in m.group(1).split(",")] if m else []

    def _extract_table(self, sql: str) -> str:
        m = re.search(r"FROM\s+(\w+)", sql, re.IGNORECASE) or re.search(r"INTO\s+(\w+)", sql, re.IGNORECASE) or re.search(r"UPDATE\s+(\w+)", sql, re.IGNORECASE)
        return m.group(1) if m else ""

    def _extract_values(self, sql: str) -> List[str]:
        m = re.search(r"VALUES\s*\((.*?)\)", sql, re.IGNORECASE)
        return [v.strip() for v in m.group(1).split(",")] if m else []

    def _extract_set(self, sql: str) -> Dict[str, str]:
        m = re.search(r"SET\s+(.*?)(?:WHERE|$)", sql, re.IGNORECASE)
        if not m: return {}
        pairs = {}
        for pair in m.group(1).split(","):
            if "=" in pair: k, v = pair.split("=", 1); pairs[k.strip()] = v.strip()
        return pairs

    def stats(self, sql: str) -> dict:
        parsed = self.parse(sql)
        return {"type": parsed.get("type", {}).name if parsed.get("type") else None, "table": parsed.get("table", "")}

def run():
    sp = SQLParser()
    sql = "SELECT id, name FROM users WHERE age > 18"
    print("Parsed:", sp.parse(sql))
    print("Stats:", sp.stats(sql))

if __name__ == "__main__": run()
