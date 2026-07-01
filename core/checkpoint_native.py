#!/usr/bin/env python3
"""checkpoint_native.py — MAGNATRIX-OS Checkpoint & Rollback System"""
from __future__ import annotations
import json, shutil, threading, time, uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

@dataclass
class Checkpoint:
    id: str; timestamp: float; label: str; source_path: str; snapshot_path: str
    operation: str = "manual"; tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class CheckpointNative:
    def __init__(self, workspace: str = "./checkpoints") -> None:
        self.workspace = Path(workspace); self.workspace.mkdir(parents=True, exist_ok=True)
        self._checkpoints: List[Checkpoint] = []; self._manifest_path = self.workspace / "manifest.json"
        self._lock = threading.RLock(); self._snapshots_dir = self.workspace / "snapshots"; self._snapshots_dir.mkdir(exist_ok=True); self._load_manifest()

    def _load_manifest(self) -> None:
        if self._manifest_path.exists():
            try:
                with open(self._manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._checkpoints = [Checkpoint(**c) for c in data.get("checkpoints", [])]
            except Exception: self._checkpoints = []

    def _save_manifest(self) -> None:
        with open(self._manifest_path, "w", encoding="utf-8") as f:
            json.dump({"checkpoints": [asdict(c) for c in self._checkpoints], "count": len(self._checkpoints), "last_updated": time.time()}, f, indent=2)

    def create(self, source_path: str, label: str = "", operation: str = "manual", tags: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        with self._lock:
            cp_id = f"cp_{int(time.time())}_{str(uuid.uuid4())[:8]}"
            source = Path(source_path).resolve(); snapshot = self._snapshots_dir / cp_id
            if not source.exists(): raise FileNotFoundError(f"Source path does not exist: {source}")
            if source.is_dir(): shutil.copytree(source, snapshot, dirs_exist_ok=True)
            else: snapshot.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, snapshot)
            checkpoint = Checkpoint(id=cp_id, timestamp=time.time(), label=label or f"Snapshot of {source.name}", source_path=str(source), snapshot_path=str(snapshot), operation=operation, tags=tags or [], metadata=metadata or {})
            self._checkpoints.append(checkpoint); self._save_manifest(); return cp_id

    def auto_snapshot(self, source_path: str, operation: str) -> str:
        return self.create(source_path=source_path, label=f"Auto before {operation}", operation=operation, tags=["auto", "pre_operation"])

    def list_checkpoints(self, source_filter: Optional[str] = None) -> List[Checkpoint]:
        with self._lock:
            cps = list(self._checkpoints)
            if source_filter: cps = [c for c in cps if source_filter in c.source_path]
            return sorted(cps, key=lambda c: c.timestamp, reverse=True)

    def get_checkpoint(self, cp_id: str) -> Optional[Checkpoint]:
        with self._lock:
            for c in self._checkpoints:
                if c.id == cp_id: return c
            return None

    def rollback(self, cp_id: str, force: bool = False) -> bool:
        with self._lock:
            checkpoint = self.get_checkpoint(cp_id)
            if checkpoint is None: return False
            source = Path(checkpoint.source_path); snapshot = Path(checkpoint.snapshot_path)
            if not snapshot.exists(): return False
            if not force:
                safety_id = self.create(source_path=str(source), label=f"Safety snapshot before rollback to {cp_id}", operation="rollback_safety", tags=["safety", "pre_rollback"], metadata={"rollback_to": cp_id})
            if source.exists():
                if source.is_dir(): shutil.rmtree(source)
                else: source.unlink()
            if snapshot.is_dir(): shutil.copytree(snapshot, source, dirs_exist_ok=True)
            else: source.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(snapshot, source)
            return True

    def rollback_last(self, source_path: str) -> Optional[str]:
        cps = self.list_checkpoints(source_path)
        if not cps: return None
        last = cps[0]
        if self.rollback(last.id): return last.id
        return None

    def diff(self, cp_id: str) -> List[str]:
        checkpoint = self.get_checkpoint(cp_id)
        if checkpoint is None: return []
        source = Path(checkpoint.source_path); snapshot = Path(checkpoint.snapshot_path); diffs = []
        def compare_dirs(snap_dir: Path, curr_dir: Path, prefix: str = "") -> None:
            snap_files = {f.relative_to(snap_dir): f for f in snap_dir.rglob("*") if f.is_file()}
            curr_files = {f.relative_to(curr_dir): f for f in curr_dir.rglob("*") if f.is_file()}
            for rel, snap_file in snap_files.items():
                if rel not in curr_files: diffs.append(f"{prefix}{rel}: deleted in current"); continue
                curr_file = curr_files[rel]
                if snap_file.read_bytes() != curr_file.read_bytes(): diffs.append(f"{prefix}{rel}: modified")
            for rel in curr_files:
                if rel not in snap_files: diffs.append(f"{prefix}{rel}: added in current")
        if source.exists() and snapshot.exists():
            if source.is_dir() and snapshot.is_dir(): compare_dirs(snapshot, source)
            elif source.is_file() and snapshot.is_file():
                if source.read_bytes() != snapshot.read_bytes(): diffs.append(f"{source.name}: modified")
            else: diffs.append("type mismatch (file vs dir)")
        return diffs

    def delete_checkpoint(self, cp_id: str) -> bool:
        with self._lock:
            checkpoint = self.get_checkpoint(cp_id)
            if checkpoint is None: return False
            snapshot = Path(checkpoint.snapshot_path)
            if snapshot.exists():
                if snapshot.is_dir(): shutil.rmtree(snapshot)
                else: snapshot.unlink()
            self._checkpoints = [c for c in self._checkpoints if c.id != cp_id]; self._save_manifest(); return True

    def prune(self, max_age_days: float = 30.0, max_count: int = 100) -> int:
        with self._lock:
            now = time.time(); cutoff = now - (max_age_days * 86400)
            to_remove = [c for c in self._checkpoints if c.timestamp < cutoff]
            if len(self._checkpoints) - len(to_remove) > max_count:
                sorted_cps = sorted(self._checkpoints, key=lambda c: c.timestamp)
                excess = len(sorted_cps) - max_count; to_remove.extend(sorted_cps[:excess])
            removed = 0
            for c in to_remove:
                if self.delete_checkpoint(c.id): removed += 1
            return removed

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_size = 0
            for c in self._checkpoints:
                snap = Path(c.snapshot_path)
                if snap.exists():
                    if snap.is_dir(): total_size += sum(f.stat().st_size for f in snap.rglob("*") if f.is_file())
                    else: total_size += snap.stat().st_size
            return {"total_checkpoints": len(self._checkpoints), "total_size_bytes": total_size, "total_size_mb": round(total_size / (1024 * 1024), 2), "sources": list(set(c.source_path for c in self._checkpoints))}

    def context_manager(self, source_path: str, operation: str) -> "CheckpointContext":
        return CheckpointContext(self, source_path, operation)

class CheckpointContext:
    def __init__(self, cp: "CheckpointNative", source_path: str, operation: str) -> None:
        self.cp = cp; self.source_path = source_path; self.operation = operation; self.checkpoint_id: Optional[str] = None
    def __enter__(self) -> "CheckpointContext":
        self.checkpoint_id = self.cp.auto_snapshot(self.source_path, self.operation); return self
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None and self.checkpoint_id: self.cp.rollback(self.checkpoint_id, force=True); return False
        return False

if __name__ == "__main__":
    cp = CheckpointNative(); test_dir = Path("./test_checkpoint_src"); test_dir.mkdir(exist_ok=True); (test_dir / "file.txt").write_text("original")
    cp_id = cp.auto_snapshot(str(test_dir), "test_write"); print("Checkpoint created:", cp_id)
    (test_dir / "file.txt").write_text("modified"); print("Diff:", cp.diff(cp_id))
    cp.rollback(cp_id); print("After rollback:", (test_dir / "file.txt").read_text())
    shutil.rmtree(test_dir, ignore_errors=True); print("Stats:", cp.get_stats())
