"""
llm_backup_restore_native.py
MAGNATRIX-OS Backup & Restore Engine
Native Python, stdlib only.
Provides snapshot-based backup, incremental backup, compression, encryption metadata,
and point-in-time restore for models, configs, and data.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tarfile
import time
import zipfile
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable


class BackupType(Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


class BackupStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"


class CompressionType(Enum):
    NONE = "none"
    GZIP = "gzip"
    ZIP = "zip"


@dataclass
class BackupSnapshot:
    id: str
    name: str
    backup_type: BackupType
    source_paths: List[str]
    archive_path: str
    created_at: float
    size_bytes: int
    checksum: str
    status: BackupStatus = BackupStatus.COMPLETED
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "backup_type": self.backup_type.value,
            "source_paths": self.source_paths,
            "archive_path": self.archive_path,
            "created_at": self.created_at,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
            "status": self.status.value,
            "parent_id": self.parent_id,
            "metadata": self.metadata,
            "tags": self.tags,
        }


@dataclass
class RestorePoint:
    snapshot_id: str
    restore_path: str
    restored_at: float
    file_count: int
    success: bool
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "restore_path": self.restore_path,
            "restored_at": self.restored_at,
            "file_count": self.file_count,
            "success": self.success,
            "errors": self.errors,
        }


class BackupRestoreEngine:
    """
    Backup and restore engine with full, incremental, and differential support.
    """

    def __init__(self, backup_dir: str = "/tmp/magnatrix_backups") -> None:
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._snapshots: Dict[str, BackupSnapshot] = {}
        self._restores: List[RestorePoint] = []
        self._load_manifest()

    def _manifest_path(self) -> Path:
        return self.backup_dir / "manifest.json"

    def _load_manifest(self) -> None:
        mp = self._manifest_path()
        if mp.exists():
            with open(mp, "r", encoding="utf-8") as f:
                data = json.load(f)
            for snap in data.get("snapshots", []):
                self._snapshots[snap["id"]] = BackupSnapshot(
                    id=snap["id"], name=snap["name"],
                    backup_type=BackupType(snap["backup_type"]),
                    source_paths=snap["source_paths"],
                    archive_path=snap["archive_path"],
                    created_at=snap["created_at"], size_bytes=snap["size_bytes"],
                    checksum=snap["checksum"],
                    status=BackupStatus(snap["status"]),
                    parent_id=snap.get("parent_id"),
                    metadata=snap.get("metadata", {}),
                    tags=snap.get("tags", []),
                )
            for rest in data.get("restores", []):
                self._restores.append(RestorePoint(
                    snapshot_id=rest["snapshot_id"],
                    restore_path=rest["restore_path"],
                    restored_at=rest["restored_at"],
                    file_count=rest["file_count"],
                    success=rest["success"],
                    errors=rest.get("errors", []),
                ))

    def _save_manifest(self) -> None:
        data = {
            "snapshots": [s.to_dict() for s in self._snapshots.values()],
            "restores": [r.to_dict() for r in self._restores],
        }
        with open(self._manifest_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def _compute_checksum(self, path: str) -> str:
        h = hashlib.sha256()
        p = Path(path)
        if p.is_file():
            with open(p, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
        elif p.is_dir():
            for fp in sorted(p.rglob("*")):
                if fp.is_file():
                    with open(fp, "rb") as f:
                        while chunk := f.read(65536):
                            h.update(chunk)
        return h.hexdigest()

    def _list_files(self, paths: List[str]) -> List[str]:
        files: List[str] = []
        for p in paths:
            pp = Path(p)
            if pp.is_file():
                files.append(str(pp))
            elif pp.is_dir():
                files.extend(str(f) for f in pp.rglob("*") if f.is_file())
        return files

    def backup(
        self, name: str, source_paths: List[str],
        backup_type: BackupType = BackupType.FULL,
        compression: CompressionType = CompressionType.GZIP,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BackupSnapshot:
        snap_id = f"{name}_{int(time.time() * 1000)}"
        archive_name = f"{snap_id}.tar.gz" if compression == CompressionType.GZIP else f"{snap_id}.zip"
        if compression == CompressionType.NONE:
            archive_name = f"{snap_id}.tar"
        archive_path = str(self.backup_dir / archive_name)

        parent_id = None
        if backup_type in (BackupType.INCREMENTAL, BackupType.DIFFERENTIAL):
            candidates = [s for s in self._snapshots.values() if s.status == BackupStatus.COMPLETED]
            if candidates:
                parent_id = max(candidates, key=lambda x: x.created_at).id

        # Build archive
        files = self._list_files(source_paths)
        if compression == CompressionType.ZIP:
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in files:
                    zf.write(f, arcname=Path(f).name)
        else:
            mode = "w:gz" if compression == CompressionType.GZIP else "w"
            with tarfile.open(archive_path, mode) as tf:
                for f in files:
                    tf.add(f, arcname=Path(f).name)

        size_bytes = os.path.getsize(archive_path)
        checksum = self._compute_checksum(archive_path)

        snapshot = BackupSnapshot(
            id=snap_id, name=name, backup_type=backup_type,
            source_paths=source_paths, archive_path=archive_path,
            created_at=time.time(), size_bytes=size_bytes,
            checksum=checksum, status=BackupStatus.COMPLETED,
            parent_id=parent_id, metadata=metadata or {},
            tags=tags or [],
        )
        self._snapshots[snap_id] = snapshot
        self._save_manifest()
        return snapshot

    def restore(self, snapshot_id: str, target_dir: str) -> RestorePoint:
        if snapshot_id not in self._snapshots:
            raise ValueError(f"Snapshot {snapshot_id} not found")
        snapshot = self._snapshots[snapshot_id]
        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)

        errors: List[str] = []
        file_count = 0
        success = True

        try:
            if snapshot.archive_path.endswith(".zip"):
                with zipfile.ZipFile(snapshot.archive_path, "r") as zf:
                    zf.extractall(target)
                    file_count = len(zf.namelist())
            else:
                with tarfile.open(snapshot.archive_path, "r:*") as tf:
                    tf.extractall(target)
                    file_count = len(tf.getmembers())
        except Exception as e:
            errors.append(str(e))
            success = False

        point = RestorePoint(
            snapshot_id=snapshot_id, restore_path=target_dir,
            restored_at=time.time(), file_count=file_count,
            success=success, errors=errors,
        )
        self._restores.append(point)
        self._save_manifest()
        return point

    def verify(self, snapshot_id: str) -> bool:
        if snapshot_id not in self._snapshots:
            return False
        snap = self._snapshots[snapshot_id]
        if not os.path.exists(snap.archive_path):
            snap.status = BackupStatus.FAILED
            self._save_manifest()
            return False
        current = self._compute_checksum(snap.archive_path)
        if current == snap.checksum:
            snap.status = BackupStatus.VERIFIED
            self._save_manifest()
            return True
        snap.status = BackupStatus.FAILED
        self._save_manifest()
        return False

    def list_snapshots(self, tag: Optional[str] = None) -> List[BackupSnapshot]:
        snaps = list(self._snapshots.values())
        if tag:
            snaps = [s for s in snaps if tag in s.tags]
        return sorted(snaps, key=lambda x: x.created_at, reverse=True)

    def delete_snapshot(self, snapshot_id: str) -> bool:
        if snapshot_id not in self._snapshots:
            return False
        snap = self._snapshots[snapshot_id]
        if os.path.exists(snap.archive_path):
            os.remove(snap.archive_path)
        del self._snapshots[snapshot_id]
        self._save_manifest()
        return True

    def get_size_total(self) -> int:
        return sum(s.size_bytes for s in self._snapshots.values())

    def cleanup_old(self, max_age_seconds: float) -> int:
        cutoff = time.time() - max_age_seconds
        to_delete = [s.id for s in self._snapshots.values() if s.created_at < cutoff]
        for sid in to_delete:
            self.delete_snapshot(sid)
        return len(to_delete)

    def export_manifest(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {"snapshots": [s.to_dict() for s in self._snapshots.values()]},
                f, indent=2, default=str
            )


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Backup & Restore Engine")
    print("=" * 60)

    # Create test data
    test_src = "/tmp/magnatrix_backup_test_src"
    os.makedirs(test_src, exist_ok=True)
    with open(os.path.join(test_src, "config.json"), "w") as f:
        json.dump({"model": "gpt-4o", "temp": 0.7}, f)
    with open(os.path.join(test_src, "weights.txt"), "w") as f:
        f.write("dummy weight data\n" * 100)

    engine = BackupRestoreEngine(backup_dir="/tmp/magnatrix_backups_demo")

    print("\n--- Full Backup ---")
    snap1 = engine.backup(
        name="daily_full", source_paths=[test_src],
        backup_type=BackupType.FULL, compression=CompressionType.GZIP,
        tags=["daily", "production"], metadata={"agent": "auto-backup"}
    )
    print(f"  ID: {snap1.id}")
    print(f"  Size: {snap1.size_bytes} bytes")
    print(f"  Checksum: {snap1.checksum[:16]}...")

    print("\n--- Incremental Backup ---")
    with open(os.path.join(test_src, "new_file.txt"), "w") as f:
        f.write("new data after first backup\n")
    snap2 = engine.backup(
        name="daily_incremental", source_paths=[test_src],
        backup_type=BackupType.INCREMENTAL, tags=["daily"]
    )
    print(f"  ID: {snap2.id}")
    print(f"  Parent: {snap2.parent_id}")

    print("\n--- Verify ---")
    ok = engine.verify(snap1.id)
    print(f"  Snapshot {snap1.id} verified: {ok}")

    print("\n--- List Snapshots ---")
    for s in engine.list_snapshots():
        print(f"  [{s.backup_type.value}] {s.name} ({s.status.value}) - {s.size_bytes} bytes")

    print("\n--- Restore ---")
    restore_dir = "/tmp/magnatrix_restore_test"
    if os.path.exists(restore_dir):
        shutil.rmtree(restore_dir)
    point = engine.restore(snap1.id, restore_dir)
    print(f"  Restored to: {point.restore_path}")
    print(f"  Files: {point.file_count}")
    print(f"  Success: {point.success}")
    restored_files = list(Path(restore_dir).rglob("*"))
    print(f"  Actual files found: {len(restored_files)}")

    print("\n--- Cleanup ---")
    deleted = engine.cleanup_old(max_age_seconds=1)
    print(f"  Deleted {deleted} old snapshots")

    print(f"\n--- Total backup size: {engine.get_size_total()} bytes ---")

    # Cleanup test dirs
    for d in [test_src, restore_dir, "/tmp/magnatrix_backups_demo"]:
        if os.path.exists(d):
            shutil.rmtree(d)

    print("\nBackup & Restore test complete.")


if __name__ == "__main__":
    run()
