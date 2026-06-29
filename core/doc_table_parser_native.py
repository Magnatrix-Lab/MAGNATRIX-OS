"""Doc Table Parser - Extract and structure tables from documents."""
from __future__ import annotations
import json, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

@dataclass
class TableCell:
    cell_id: str
    row: int
    col: int
    content: str = ""
    rowspan: int = 1
    colspan: int = 1
    header: bool = False

    def to_dict(self) -> Dict:
        return {"cell_id": self.cell_id, "row": self.row, "col": self.col,
                "content": self.content, "rowspan": self.rowspan, "colspan": self.colspan, "header": self.header}

@dataclass
class ParsedTable:
    table_id: str
    page_number: int = 0
    rows: int = 0
    cols: int = 0
    cells: List[TableCell] = field(default_factory=list)
    caption: str = ""

    def to_dict(self) -> Dict:
        return {"table_id": self.table_id, "page_number": self.page_number, "rows": self.rows,
                "cols": self.cols, "cells": [c.to_dict() for c in self.cells], "caption": self.caption}

    def to_markdown(self) -> str:
        if not self.cells: return ""
        grid = [["" for _ in range(self.cols)] for _ in range(self.rows)]
        for c in self.cells:
            if 0 <= c.row < self.rows and 0 <= c.col < self.cols:
                grid[c.row][c.col] = c.content
        lines = []
        NL = chr(10)
        for i, row in enumerate(grid):
            lines.append("| " + " | ".join(row) + " |")
            if i == 0:
                lines.append("|" + "|".join(["---"] * self.cols) + "|")
        return NL.join(lines)

class DocTableParser:
    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "doc_table"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.tables: Dict[str, ParsedTable] = {}
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for t in data.get("tables",[]):
                    cells = [TableCell(**c) for c in t.pop("cells",[])]
                    self.tables[t["table_id"]] = ParsedTable(cells=cells, **t)
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"tables": [t.to_dict() for t in self.tables.values()]}, indent=2))

    def parse_from_text(self, lines: List[str], page_number: int = 1, table_id: str = "") -> ParsedTable:
        if not table_id: table_id = "table_" + str(page_number) + "_" + str(int(time.time()))
        if not lines: return ParsedTable(table_id=table_id)
        cells = []
        max_cols = 0
        for ri, line in enumerate(lines):
            parts = line.split(chr(9)) if chr(9) in line else [line]
            max_cols = max(max_cols, len(parts))
            for ci, part in enumerate(parts):
                cells.append(TableCell(
                    cell_id=table_id + "_r" + str(ri) + "_c" + str(ci),
                    row=ri, col=ci, content=part.strip(), header=(ri==0)))
        table = ParsedTable(table_id=table_id, page_number=page_number, rows=len(lines), cols=max_cols, cells=cells)
        self.tables[table_id] = table
        self._save_state()
        return table

    def parse_from_grid(self, grid: List[List[str]], page_number: int = 1, table_id: str = "") -> ParsedTable:
        if not table_id: table_id = "table_" + str(page_number) + "_" + str(int(time.time()))
        cells = []
        for ri, row in enumerate(grid):
            for ci, content in enumerate(row):
                cells.append(TableCell(
                    cell_id=table_id + "_r" + str(ri) + "_c" + str(ci),
                    row=ri, col=ci, content=content, header=(ri==0)))
        table = ParsedTable(table_id=table_id, page_number=page_number, rows=len(grid),
                            cols=max(len(r) for r in grid) if grid else 0, cells=cells)
        self.tables[table_id] = table
        self._save_state()
        return table

    def get_stats(self) -> Dict:
        return {"tables_total": len(self.tables), "cells_total": sum(len(t.cells) for t in self.tables.values()),
                "avg_rows": round(sum(t.rows for t in self.tables.values())/max(1,len(self.tables)),1)}

    def to_dict(self) -> Dict:
        return {"tables": [t.to_dict() for t in self.tables.values()], "stats": self.get_stats()}

__all__ = ["DocTableParser", "ParsedTable", "TableCell"]
