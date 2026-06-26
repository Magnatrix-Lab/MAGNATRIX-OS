#!/usr/bin/env python3
"""Backup Engine v2 for MAGNATRIX-OS — Incremental backup with deduplication."""
from __future__ import annotations
import hashlib, json, os, shutil, time
from pathlib import Path
from typing import Any, Dict, List

class BackupEngineV2:
    def __init__(self, backup_dir: str = "./data/backups") -> None:
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._chunks: Dict[str, str] = {}  # hash -> chunk path

    def _chunk_hash(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()[:16]

    def backup(self, source_dir: str, incremental: bool = True) -> str:
        src = Path(source_dir)
        timestamp = int(time.time())
        backup_path = self.backup_dir / f"backup_{timestamp}"
        backup_path.mkdir(parents=True, exist_ok=True)

        manifest = {"files": [], "timestamp": timestamp}
        for f in src.rglob("*"):
            if f.is_file():
                data = f.read_bytes()
                h = self._chunk_hash(data)
                if h not in self._chunks or not incremental:
                    chunk_path = self.backup_dir / "chunks" / h
                    chunk_path.parent.mkdir(parents=True, exist_ok=True)
                    chunk_path.write_bytes(data)
                    self._chunks[h] = str(chunk_path)
                manifest["files"].append({"path": str(f.relative_to(src)), "hash": h})

        (backup_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return str(backup_path)

    def stats(self) -> Dict[str, Any]:
        total_size = sum(f.stat().st_size for f in self.backup_dir.rglob("*") if f.is_file())
        return {"backups": len(list(self.backup_dir.glob("backup_*"))), "chunks": len(self._chunks), "total_size_mb": total_size // (1024*1024)}
