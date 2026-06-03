"""LLM Data Frame Engine — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

@dataclass
class DataFrameColumn:
    name: str
    values: List[Any]
    dtype: str = "object"

class DataFrameEngine:
    def __init__(self) -> None:
        self._columns: Dict[str, DataFrameColumn] = {}
        self._index: List[str] = []

    def add_column(self, column: DataFrameColumn) -> None:
        self._columns[column.name] = column
        if not self._index:
            self._index = [str(i) for i in range(len(column.values))]

    def get_column(self, name: str) -> Optional[DataFrameColumn]:
        return self._columns.get(name)

    def get_row(self, idx: int) -> Dict[str, Any]:
        return {name: col.values[idx] for name, col in self._columns.items() if idx < len(col.values)}

    def filter(self, column: str, predicate: Callable[[Any], bool]) -> List[int]:
        col = self._columns.get(column)
        if not col:
            return []
        return [i for i, v in enumerate(col.values) if predicate(v)]

    def aggregate(self, column: str, func: Callable[[List[Any]], Any]) -> Any:
        col = self._columns.get(column)
        if not col:
            return None
        return func(col.values)

    def group_by(self, column: str) -> Dict[str, List[int]]:
        col = self._columns.get(column)
        if not col:
            return {}
        groups = {}
        for i, v in enumerate(col.values):
            key = str(v)
            if key not in groups:
                groups[key] = []
            groups[key].append(i)
        return groups

    def get_stats(self) -> Dict[str, Any]:
        return {"columns": len(self._columns), "rows": len(self._index)}

def run() -> None:
    print("Data Frame Engine test")
    e = DataFrameEngine()
    e.add_column(DataFrameColumn("name", ["Alice", "Bob", "Charlie"]))
    e.add_column(DataFrameColumn("age", [30, 25, 35]))
    e.add_column(DataFrameColumn("score", [85, 90, 78]))
    print("  Row 0: " + str(e.get_row(0)))
    print("  Filter age > 28: " + str(e.filter("age", lambda x: x > 28)))
    print("  Avg score: " + str(e.aggregate("score", lambda x: sum(x) / len(x))))
    print("  Stats: " + str(e.get_stats()))
    print("Data Frame Engine test complete.")

if __name__ == "__main__":
    run()
