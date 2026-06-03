"""LLM Data Ingestor — Native Python (stdlib only)."""
from __future__ import annotations
import json, csv, os
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Iterator
from enum import Enum, auto

class IngestFormat(Enum):
    JSON = auto()
    CSV = auto()
    TEXT = auto()
    LINES = auto()

@dataclass
class DataRecord:
    id: str
    source: str
    content: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

class DataIngestor:
    def __init__(self) -> None:
        self._records: List[DataRecord] = []
        self._index: int = 0

    def ingest_json(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            for item in data:
                self._add_record(item, path)
        else:
            self._add_record(data, path)

    def ingest_csv(self, path: str) -> None:
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self._add_record(dict(row), path)

    def ingest_text(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self._add_record({"text": content}, path)

    def ingest_lines(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                self._add_record({"line": line.strip(), "line_number": i + 1}, path)

    def _add_record(self, content: Dict[str, Any], source: str) -> None:
        self._index += 1
        self._records.append(DataRecord("rec_" + str(self._index), source, content))

    def get_all(self) -> List[DataRecord]:
        return list(self._records)

    def get_stats(self) -> Dict[str, Any]:
        sources = {}
        for r in self._records:
            sources[r.source] = sources.get(r.source, 0) + 1
        return {"total": len(self._records), "sources": sources}

def run() -> None:
    print("Data Ingestor test")
    e = DataIngestor()
    e._add_record({"name": "Alice", "age": 30}, "manual")
    e._add_record({"name": "Bob", "age": 25}, "manual")
    print("  Total records: " + str(len(e.get_all())))
    print("  Stats: " + str(e.get_stats()))
    print("Data Ingestor test complete.")

if __name__ == "__main__":
    run()
