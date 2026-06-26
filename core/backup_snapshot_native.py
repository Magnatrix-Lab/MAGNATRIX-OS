#!/usr/bin/env python3
"""
Backup & Snapshot Manager for MAGNATRIX-OS
Creates timestamped snapshots of the repository, supports restore,
rollback, and differential tracking. Uses tarfile + hash verification.
Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import os
import shutil
import tarfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class SnapshotStatus(enum.Enum):
    PENDING = "pending"
    COMPLETE = "complete"
    CORRUPT = "corrupt"
    RESTORED = "restored"


@dataclasses.dataclass
class SnapshotRecord:
    """Metadata for a single repository snapshot."""
    snapshot_id: str
    timestamp: float
    created_at: str
    description: str
    archive_path: str
    repo_path: str
    file_count: int
    total_bytes: int
    manifest_hash: str  # SHA-256 of file manifest
    status: SnapshotStatus
    tags: Set[str] = dataclasses.field(default_factory=set)
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "created_at": self.created_at,
            "description": self.description,
            "archive_path": self.archive_path,
            "repo_path": self.repo_path,
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
            "manifest_hash": self.manifest_hash,
            "status": self.status.value,
            "tags": sorted(self.tags),
            "metadata": self.metadata,
        }


class BackupSnapshotManager:
    """Manages repository snapshots, integrity verification, and rollback."""

    def __init__(self, repo_root: str = ".", backup_dir: str = "./backups") -> None:
        self.repo_root = Path(repo_root).resolve()
        self.backup_dir = Path(backup_dir).resolve()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.backup_dir / "snapshot_index.json"
        self._snapshots: Dict[str, SnapshotRecord] = {}
        self._load_index()

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def _load_index(self) -> None:
        if self._index_path.exists():
            try:
                with open(self._index_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    rec = SnapshotRecord(
                        snapshot_id=item["snapshot_id"],
                        timestamp=item["timestamp"],
                        created_at=item["created_at"],
                        description=item["description"],
                        archive_path=item["archive_path"],
                        repo_path=item["repo_path"],
                        file_count=item["file_count"],
                        total_bytes=item["total_bytes"],
                        manifest_hash=item["manifest_hash"],
                        status=SnapshotStatus(item["status"]),
                        tags=set(item.get("tags", [])),
                        metadata=item.get("metadata", {}),
                    )
                    self._snapshots[rec.snapshot_id] = rec
            except Exception:
                pass

    def _save_index(self) -> None:
        data = [s.to_dict() for s in self._snapshots.values()]
        with open(self._index_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Snapshot creation
    # ------------------------------------------------------------------

    def _build_manifest(self) -> Tuple[Dict[str, str], int, int]:
        """Return (relative_path -> sha256, file_count, total_bytes)."""
        manifest: Dict[str, str] = {}
        count = 0
        total = 0
        exclude = {"__pycache__", ".git", "venv", "node_modules", "dist", "build", ".pytest_cache", "*.pyc"}
        for path in self.repo_root.rglob("*"):
            if any(part in exclude for part in path.parts):
                continue
            if path.is_file():
                rel = str(path.relative_to(self.repo_root)).replace("\\", "/")
                try:
                    content = path.read_bytes()
                    manifest[rel] = hashlib.sha256(content).hexdigest()
                    count += 1
                    total += len(content)
                except Exception:
                    pass
        return manifest, count, total

    def create(
        self,
        description: str = "",
        tags: Optional[Set[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> SnapshotRecord:
        snapshot_id = f"snap_{int(time.time())}"
        archive_name = f"{snapshot_id}.tar.gz"
        archive_path = self.backup_dir / archive_name

        manifest, file_count, total_bytes = self._build_manifest()
        manifest_hash = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()

        # Write tar.gz
        with tarfile.open(archive_path, "w:gz") as tar:
            for rel in sorted(manifest.keys()):
                abs_path = self.repo_root / rel
                tar.add(abs_path, arcname=rel)

        record = SnapshotRecord(
            snapshot_id=snapshot_id,
            timestamp=time.time(),
            created_at=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            description=description or f"Snapshot of {self.repo_root.name}",
            archive_path=str(archive_path),
            repo_path=str(self.repo_root),
            file_count=file_count,
            total_bytes=total_bytes,
            manifest_hash=manifest_hash,
            status=SnapshotStatus.COMPLETE,
            tags=tags or set(),
            metadata={"manifest_keys": list(manifest.keys())[:100]},  # cap metadata
        )
        self._snapshots[snapshot_id] = record
        self._save_index()
        return record

    # ------------------------------------------------------------------
    # Restore & rollback
    # ------------------------------------------------------------------

    def restore(self, snapshot_id: str, target_dir: Optional[str] = None, overwrite: bool = False) -> str:
        record = self._snapshots.get(snapshot_id)
        if not record:
            raise KeyError(f"Snapshot '{snapshot_id}' not found")
        if not os.path.exists(record.archive_path):
            raise FileNotFoundError(f"Archive missing: {record.archive_path}")

        target = Path(target_dir).resolve() if target_dir else self.repo_root
        if target.exists() and not overwrite:
            raise FileExistsError(f"Target exists. Set overwrite=True to replace.")

        target.mkdir(parents=True, exist_ok=True)
        with tarfile.open(record.archive_path, "r:gz") as tar:
            tar.extractall(path=str(target))
        record.status = SnapshotStatus.RESTORED
        self._save_index()
        return str(target)

    def rollback(self, snapshot_id: str) -> str:
        """Restore snapshot back into the original repo root (destructive)."""
        # Safety: create emergency backup before rollback
        emergency = self.create(description=f"Emergency pre-rollback backup for {snapshot_id}", tags={"emergency", "rollback"})
        # Wipe current repo (except .git)
        for item in self.repo_root.iterdir():
            if item.name == ".git":
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        return self.restore(snapshot_id, target_dir=str(self.repo_root), overwrite=True)

    # ------------------------------------------------------------------
    # Integrity verification
    # ------------------------------------------------------------------

    def verify(self, snapshot_id: str) -> bool:
        record = self._snapshots.get(snapshot_id)
        if not record:
            return False
        if not os.path.exists(record.archive_path):
            record.status = SnapshotStatus.CORRUPT
            self._save_index()
            return False
        try:
            with tarfile.open(record.archive_path, "r:gz") as tar:
                # Basic tar integrity check
                for member in tar.getmembers():
                    tar.extractfile(member)
            return True
        except Exception:
            record.status = SnapshotStatus.CORRUPT
            self._save_index()
            return False

    def verify_all(self) -> Dict[str, bool]:
        return {sid: self.verify(sid) for sid in self._snapshots}

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def compare(self, snap_a: str, snap_b: str) -> Dict[str, Any]:
        """Compare two snapshots and return added/removed/changed files."""
        def _get_manifest(sid: str) -> Dict[str, str]:
            rec = self._snapshots.get(sid)
            if not rec:
                return {}
            # Reconstruct from archive
            manifest: Dict[str, str] = {}
            with tarfile.open(rec.archive_path, "r:gz") as tar:
                for member in tar.getmembers():
                    if member.isfile():
                        f = tar.extractfile(member)
                        if f:
                            content = f.read()
                            manifest[member.name] = hashlib.sha256(content).hexdigest()
            return manifest

        m_a = _get_manifest(snap_a)
        m_b = _get_manifest(snap_b)
        keys_a = set(m_a.keys())
        keys_b = set(m_b.keys())
        return {
            "added": sorted(keys_b - keys_a),
            "removed": sorted(keys_a - keys_b),
            "changed": sorted([k for k in keys_a & keys_b if m_a[k] != m_b[k]]),
            "unchanged": sorted([k for k in keys_a & keys_b if m_a[k] == m_b[k]]),
        }

    # ------------------------------------------------------------------
    # Listing & cleanup
    # ------------------------------------------------------------------

    def list_all(self) -> List[SnapshotRecord]:
        return sorted(self._snapshots.values(), key=lambda s: s.timestamp, reverse=True)

    def get(self, snapshot_id: str) -> Optional[SnapshotRecord]:
        return self._snapshots.get(snapshot_id)

    def delete(self, snapshot_id: str) -> bool:
        record = self._snapshots.pop(snapshot_id, None)
        if record and os.path.exists(record.archive_path):
            os.remove(record.archive_path)
            self._save_index()
            return True
        return False

    def prune(self, keep_count: int = 10) -> int:
        """Keep only the most recent N snapshots, delete the rest."""
        all_snaps = self.list_all()
        removed = 0
        for old in all_snaps[keep_count:]:
            if self.delete(old.snapshot_id):
                removed += 1
        return removed

    def prune_by_age(self, max_age_days: int = 30) -> int:
        cutoff = time.time() - (max_age_days * 86400)
        removed = 0
        for sid, rec in list(self._snapshots.items()):
            if rec.timestamp < cutoff and "emergency" not in rec.tags:
                if self.delete(sid):
                    removed += 1
        return removed

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        total = len(self._snapshots)
        total_size = sum(s.total_bytes for s in self._snapshots.values())
        archive_disk = 0
        for s in self._snapshots.values():
            if os.path.exists(s.archive_path):
                archive_disk += os.path.getsize(s.archive_path)
        return {
            "total_snapshots": total,
            "total_files_snapshotted": sum(s.file_count for s in self._snapshots.values()),
            "total_bytes_original": total_size,
            "total_archive_disk_bytes": archive_disk,
            "backup_directory": str(self.backup_dir),
        }

    def export_index(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([s.to_dict() for s in self._snapshots.values()], f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    import tempfile
    tmp_repo = Path(tempfile.mkdtemp(prefix="magnatrix_repo_"))
    tmp_backup = Path(tempfile.mkdtemp(prefix="magnatrix_backup_"))
    # Create dummy repo structure
    (tmp_repo / "core").mkdir()
    (tmp_repo / "governance").mkdir()
    (tmp_repo / "core" / "module.py").write_text("print('hello')\n")
    (tmp_repo / "governance" / "policy.py").write_text("x = 42\n")
    (tmp_repo / "README.md").write_text("# MAGNATRIX-OS\n")

    mgr = BackupSnapshotManager(str(tmp_repo), str(tmp_backup))
    print("=== Backup & Snapshot Manager Demo ===\n")
    # Create snapshot
    snap1 = mgr.create(description="Initial clean state", tags={"baseline"})
    print(f"Created snapshot: {snap1.snapshot_id}")
    print(f"  Files: {snap1.file_count} | Bytes: {snap1.total_bytes} | Hash: {snap1.manifest_hash[:16]}...")
    # Modify repo
    (tmp_repo / "core" / "new_module.py").write_text("y = 100\n")
    snap2 = mgr.create(description="After adding new_module", tags={"feature"})
    print(f"\nCreated snapshot: {snap2.snapshot_id}")
    # Compare
    diff = mgr.compare(snap1.snapshot_id, snap2.snapshot_id)
    print(f"\nDiff {snap1.snapshot_id} -> {snap2.snapshot_id}:")
    print(f"  Added: {diff['added']}")
    print(f"  Removed: {diff['removed']}")
    print(f"  Changed: {diff['changed']}")
    # Verify
    print(f"\nVerify snap1: {mgr.verify(snap1.snapshot_id)}")
    # Stats
    print(f"\nStats: {mgr.stats()}")
    # Cleanup
    shutil.rmtree(tmp_repo)
    shutil.rmtree(tmp_backup)
    print("\nCleanup complete.")


if __name__ == "__main__":
    _demo()
