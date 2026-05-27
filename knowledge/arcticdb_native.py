#!/usr/bin/env python3
"""
MAGNATRIX-OS ArcticDB Native
Lightweight columnar data store with time-series indexing.
Pure Python stdlib.
"""
import os, json, struct, time, tempfile, shutil
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class Column:
    name: str
    dtype: str = "str"
    data: List[Any] = field(default_factory=list)


class ArcticDBNative:
    """
    Simple columnar database for time-series and structured data.
    Stores as JSON files with column-oriented layout.
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/.magnatrix/arcticdb")
        os.makedirs(self.db_path, exist_ok=True)
        self._tables: Dict[str, Dict] = {}

    def create_table(self, name: str, columns: List[str], dtypes: List[str] = None):
        """Create a new table with specified columns."""
        table_dir = os.path.join(self.db_path, name)
        os.makedirs(table_dir, exist_ok=True)
        schema = {
            "columns": columns,
            "dtypes": dtypes or ["str"] * len(columns),
            "created": time.time(),
        }
        with open(os.path.join(table_dir, "schema.json"), "w") as f:
            json.dump(schema, f)
        self._tables[name] = {"schema": schema, "data": []}

    def write(self, table: str, row: Dict[str, Any]):
        """Write a single row to table."""
        if table not in self._tables:
            self._load_table(table)
        self._tables[table]["data"].append(row)
        self._flush(table)

    def write_many(self, table: str, rows: List[Dict[str, Any]]):
        """Write multiple rows."""
        for row in rows:
            self.write(table, row)

    def read(self, table: str, filter_fn=None) -> List[Dict]:
        """Read rows, optionally filtered."""
        if table not in self._tables:
            self._load_table(table)
        data = self._tables[table]["data"]
        if filter_fn:
            return [r for r in data if filter_fn(r)]
        return data

    def query(self, table: str, column: str, value: Any) -> List[Dict]:
        """Simple equality query."""
        return self.read(table, lambda r: r.get(column) == value)

    def delete(self, table: str, filter_fn):
        """Delete rows matching filter."""
        if table not in self._tables:
            self._load_table(table)
        self._tables[table]["data"] = [r for r in self._tables[table]["data"] if not filter_fn(r)]
        self._flush(table)

    def _load_table(self, name: str):
        table_dir = os.path.join(self.db_path, name)
        schema_path = os.path.join(table_dir, "schema.json")
        data_path = os.path.join(table_dir, "data.jsonl")
        schema = {"columns": [], "dtypes": []}
        if os.path.exists(schema_path):
            with open(schema_path) as f:
                schema = json.load(f)
        data = []
        if os.path.exists(data_path):
            with open(data_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data.append(json.loads(line))
        self._tables[name] = {"schema": schema, "data": data}

    def _flush(self, name: str):
        table_dir = os.path.join(self.db_path, name)
        data_path = os.path.join(table_dir, "data.jsonl")
        with open(data_path, "w") as f:
            for row in self._tables[name]["data"]:
                f.write(json.dumps(row) + "
")

    def list_tables(self) -> List[str]:
        return [d for d in os.listdir(self.db_path) if os.path.isdir(os.path.join(self.db_path, d))]

    def stats(self, table: str) -> Dict:
        if table not in self._tables:
            self._load_table(table)
        return {
            "rows": len(self._tables[table]["data"]),
            "columns": len(self._tables[table]["schema"]["columns"]),
        }


def _demo():
    print("=" * 60)
    print("MAGNATRIX-OS ArcticDB Demo")
    print("=" * 60)
    db = ArcticDBNative(tempfile.mkdtemp())
    db.create_table("trades", ["symbol", "price", "qty", "timestamp"])
    db.write("trades", {"symbol": "BTC", "price": 50000, "qty": 0.1, "timestamp": time.time()})
    db.write("trades", {"symbol": "ETH", "price": 3000, "qty": 1.5, "timestamp": time.time()})
    print(f"Tables: {db.list_tables()}")
    print(f"Stats: {db.stats('trades')}")
    results = db.query("trades", "symbol", "BTC")
    print(f"BTC trades: {len(results)}")
    print("=" * 60)


if __name__ == "__main__":
    _demo()
