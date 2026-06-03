"""LLm Spreadsheet Engine — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from enum import Enum, auto

class CellType(Enum):
    NUMBER = auto()
    STRING = auto()
    FORMULA = auto()
    EMPTY = auto()

@dataclass
class Cell:
    row: int
    col: int
    value: Any
    cell_type: CellType = CellType.STRING
    formula: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

class SpreadsheetEngine:
    def __init__(self, rows: int = 10, cols: int = 10) -> None:
        self.rows = rows
        self.cols = cols
        self._data: Dict[str, Cell] = {}

    def _key(self, row: int, col: int) -> str:
        return str(row) + "," + str(col)

    def set(self, row: int, col: int, value: Any, formula: str = "") -> None:
        cell_type = CellType.EMPTY if value is None else (CellType.NUMBER if isinstance(value, (int, float)) else CellType.STRING)
        if formula:
            cell_type = CellType.FORMULA
        self._data[self._key(row, col)] = Cell(row, col, value, cell_type, formula)

    def get(self, row: int, col: int) -> Optional[Any]:
        cell = self._data.get(self._key(row, col))
        return cell.value if cell else None

    def get_cell(self, row: int, col: int) -> Optional[Cell]:
        return self._data.get(self._key(row, col))

    def sum_range(self, row1: int, col1: int, row2: int, col2: int) -> float:
        total = 0.0
        for r in range(row1, row2 + 1):
            for c in range(col1, col2 + 1):
                val = self.get(r, c)
                if isinstance(val, (int, float)):
                    total += val
        return total

    def avg_range(self, row1: int, col1: int, row2: int, col2: int) -> float:
        values = []
        for r in range(row1, row2 + 1):
            for c in range(col1, col2 + 1):
                val = self.get(r, c)
                if isinstance(val, (int, float)):
                    values.append(val)
        return sum(values) / len(values) if values else 0.0

    def to_csv(self) -> str:
        lines = []
        for r in range(self.rows):
            row_vals = []
            for c in range(self.cols):
                val = self.get(r, c)
                row_vals.append(str(val) if val is not None else "")
            lines.append(",".join(row_vals))
        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        counts = {}
        for cell in self._data.values():
            counts[cell.cell_type.name] = counts.get(cell.cell_type.name, 0) + 1
        return {"cells": len(self._data), "by_type": counts, "dimensions": str(self.rows) + "x" + str(self.cols)}

def run() -> None:
    print("Spreadsheet Engine test")
    e = SpreadsheetEngine(5, 5)
    e.set(0, 0, 10)
    e.set(0, 1, 20)
    e.set(0, 2, 30)
    e.set(1, 0, "Total")
    e.set(1, 1, "", "=SUM(A1:C1)")
    print("  Sum A1:C1: " + str(e.sum_range(0, 0, 0, 2)))
    print("  Avg: " + str(e.avg_range(0, 0, 0, 2)))
    print("  CSV:\n" + e.to_csv())
    print("  Stats: " + str(e.get_stats()))
    print("Spreadsheet Engine test complete.")

if __name__ == "__main__":
    run()
