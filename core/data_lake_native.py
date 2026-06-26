#!/usr/bin/env python3
"""Data Lake for MAGNATRIX-OS — Store raw data before processing."""
from __future__ import annotations
import json, os, time, hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

class DataLake:
    def __init__(self, root: str = "./data/lake") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def write(self, dataset: str, record: Any, partition: str = "default") -> str:
        path = self.root / dataset / partition
        path.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        h = hashlib.md5(json.dumps(record, sort_keys=True, default=str).encode()).hexdigest()[:8]
        fname = path / f"{ts}_{h}.json"
        fname.write_text(json.dumps(record), encoding="utf-8")
        return str(fname)

    def read(self, dataset: str, partition: str = "default") -> List[Dict[str, Any]]:
        path = self.root / dataset / partition
        if not path.exists():
            return []
        records = []
        for f in sorted(path.glob("*.json")):
            records.append(json.loads(f.read_text(encoding="utf-8")))
        return records

    def datasets(self) -> List[str]:
        return [d.name for d in self.root.iterdir() if d.is_dir()]

    def stats(self) -> Dict[str, Any]:
        total_files = sum(1 for _ in self.root.rglob("*.json"))
        total_size = sum(f.stat().st_size for f in self.root.rglob("*.json"))
        return {"datasets": len(self.datasets()), "files": total_files, "size_bytes": total_size}
