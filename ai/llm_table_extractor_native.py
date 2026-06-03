"""LLM Table Extractor — Native Python (stdlib only)."""
from __future__ import annotations
import csv, re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

@dataclass
class TableCell:
    row: int
    col: int
    value: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExtractedTable:
    id: str
    headers: List[str]
    rows: List[List[str]]
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

class TableExtractor:
    def __init__(self) -> None:
        self._tables: List[ExtractedTable] = []

    def extract_csv(self, text: str) -> ExtractedTable:
        lines = text.strip().splitlines()
        reader = csv.reader(lines)
        rows = list(reader)
        headers = rows[0] if rows else []
        data = rows[1:] if len(rows) > 1 else []
        table = ExtractedTable("csv_1", headers, data)
        self._tables.append(table)
        return table

    def extract_markdown_table(self, text: str) -> Optional[ExtractedTable]:
        lines = [l.strip() for l in text.splitlines() if l.strip().startswith("|")]
        if not lines:
            return None
        rows = []
        for line in lines:
            if "---" in line:
                continue
            cells = [c.strip() for c in line.split("|")[1:-1]]
            rows.append(cells)
        headers = rows[0] if rows else []
        data = rows[1:] if len(rows) > 1 else []
        table = ExtractedTable("md_1", headers, data)
        self._tables.append(table)
        return table

    def extract_delimited(self, text: str, delimiter: str = "\t") -> ExtractedTable:
        lines = text.strip().splitlines()
        rows = [line.split(delimiter) for line in lines]
        headers = rows[0] if rows else []
        data = rows[1:] if len(rows) > 1 else []
        table = ExtractedTable("delim_1", headers, data)
        self._tables.append(table)
        return table

    def to_dict(self, table: ExtractedTable) -> List[Dict[str, str]]:
        return [{h: row[i] if i < len(row) else "" for i, h in enumerate(table.headers)} for row in table.rows]

    def get_stats(self) -> Dict[str, Any]:
        return {"tables": len(self._tables), "total_rows": sum(len(t.rows) for t in self._tables)}

def run() -> None:
    print("Table Extractor test")
    e = TableExtractor()
    csv_text = "name,age\nAlice,30\nBob,25"
    t1 = e.extract_csv(csv_text)
    print("  CSV: " + str(t1.headers) + " -> " + str(len(t1.rows)) + " rows")
    md_text = "| a | b |\n|---|---|\n| 1 | 2 |"
    t2 = e.extract_markdown_table(md_text)
    print("  MD: " + str(t2.headers if t2 else None))
    print("  Dict: " + str(e.to_dict(t1)))
    print("  Stats: " + str(e.get_stats()))
    print("Table Extractor test complete.")

if __name__ == "__main__":
    run()
