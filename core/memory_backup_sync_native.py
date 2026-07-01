#!/usr/bin/env python3
"""memory_backup_sync_native.py — MAGNATRIX-OS Memory Backup & Cross-Device Sync

Cross-device portability, memory sync, backup/restore. Handles identity,
vector memory, knowledge graph, checkpoint data. Hermes-inspired.
Pure stdlib.
"""
from __future__ import annotations
import json
import shutil
import threading
import time
import zipfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class BackupManifest:
    id: str
    timestamp: float
    version: str
    source_device: str
    memory_modules: List[str]  # which modules backed up
    size_bytes: int = 0
    checksum: str = ""  # SHA-256 of archive
    metadata: Dict[str, Any] = field(default_factory=dict)
    encrypted: bool = False


@dataclass
class SyncState:
    device_id: str
    last_sync: float
    modules_synced: List[str]
    conflict_count: int = 0
    auto_sync: bool = True
    sync_interval: float = 3600.0  # 1 hour default
    metadata: Dict[str, Any] = field(default_factory=dict)


class MemoryBackupSyncNative:
    """Native memory backup and cross-device sync engine."""

    BACKUP_MODULES: List[str] = [
        "identity", "vector_memory", "knowledge_graph", "checkpoint",
        "agent_messaging", "task_scheduler", "deliberation_engine",
    ]

    def __init__(self, workspace: str = "./memory_backup_sync", device_id: str = "default") -> None:
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.device_id = device_id
        self._backups: List[BackupManifest] = []
        self._sync_states: Dict[str, SyncState] = {}
        self._lock = threading.RLock()
        self._backups_path = self.workspace / "backups.json"
        self._sync_path = self.workspace / "sync_states.json"
        self._load()

    def _load(self) -> None:
        if self._backups_path.exists():
            try:
                with open(self._backups_path, "r", encoding="utf-8") as f:
                    self._backups = [BackupManifest(**b) for b in json.load(f)]
            except Exception: pass
        if self._sync_path.exists():
            try:
                with open(self._sync_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for did, sd in data.items(): self._sync_states[did] = SyncState(**sd)
            except Exception: pass

    def _save(self) -> None:
        with open(self._backups_path, "w", encoding="utf-8") as f:
            json.dump([asdict(b) for b in self._backups], f, indent=2, default=str)
        with open(self._sync_path, "w", encoding="utf-8") as f:
            json.dump({did: asdict(s) for did, s in self._sync_states.items()}, f, indent=2, default=str)

    def create_backup(self, modules: Optional[List[str]] = None, source_dirs: Optional[Dict[str, str]] = None, version: str = "1.0", encrypt: bool = False) -> BackupManifest:
        """Create a backup of specified memory modules."""
        with self._lock:
            modules = modules or self.BACKUP_MODULES
            source_dirs = source_dirs or {}
            backup_id = f"backup_{int(time.time())}_{self.device_id}"
            backup_dir = self.workspace / "archives" / backup_id
            backup_dir.mkdir(parents=True, exist_ok=True)
            total_size = 0
            for module in modules:
                src = Path(source_dirs.get(module, f"./{module}"))
                if src.exists():
                    dst = backup_dir / module
                    if src.is_dir(): shutil.copytree(src, dst, dirs_exist_ok=True)
                    else: shutil.copy2(src, dst)
                    total_size += sum(f.stat().st_size for f in dst.rglob("*") if f.is_file()) if dst.is_dir() else dst.stat().st_size
            # Create archive
            archive_path = self.workspace / "archives" / f"{backup_id}.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in backup_dir.rglob("*"):
                    if f.is_file(): zf.write(f, f.relative_to(backup_dir))
            # Compute checksum
            import hashlib
            with open(archive_path, "rb") as f:
                checksum = hashlib.sha256(f.read()).hexdigest()
            archive_size = archive_path.stat().st_size
            # Cleanup temp dir
            shutil.rmtree(backup_dir, ignore_errors=True)
            manifest = BackupManifest(
                id=backup_id, timestamp=time.time(), version=version,
                source_device=self.device_id, memory_modules=modules,
                size_bytes=archive_size, checksum=checksum, encrypted=encrypt
            )
            self._backups.append(manifest)
            self._save()
            return manifest

    def restore_backup(self, backup_id: str, target_dirs: Optional[Dict[str, str]] = None, overwrite: bool = False) -> bool:
        """Restore a backup to target directories."""
        with self._lock:
            manifest = None
            for b in self._backups:
                if b.id == backup_id: manifest = b; break
            if not manifest: return False
            archive_path = self.workspace / "archives" / f"{backup_id}.zip"
            if not archive_path.exists(): return False
            # Verify checksum
            import hashlib
            with open(archive_path, "rb") as f:
                computed = hashlib.sha256(f.read()).hexdigest()
            if computed != manifest.checksum: return False
            # Extract
            restore_dir = self.workspace / "restore" / backup_id
            restore_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(restore_dir)
            # Copy to targets
            target_dirs = target_dirs or {}
            for module in manifest.memory_modules:
                src = restore_dir / module
                if not src.exists(): continue
                dst = Path(target_dirs.get(module, f"./{module}"))
                if dst.exists() and not overwrite: continue
                if dst.exists():
                    if dst.is_dir(): shutil.rmtree(dst)
                    else: dst.unlink()
                if src.is_dir(): shutil.copytree(src, dst)
                else: shutil.copy2(src, dst)
            # Cleanup restore dir
            shutil.rmtree(restore_dir, ignore_errors=True)
            return True

    def list_backups(self, device_id: Optional[str] = None) -> List[BackupManifest]:
        with self._lock:
            backups = self._backups
            if device_id: backups = [b for b in backups if b.source_device == device_id]
            return sorted(backups, key=lambda b: b.timestamp, reverse=True)

    def delete_backup(self, backup_id: str) -> bool:
        with self._lock:
            for i, b in enumerate(self._backups):
                if b.id == backup_id:
                    archive_path = self.workspace / "archives" / f"{backup_id}.zip"
                    if archive_path.exists(): archive_path.unlink()
                    self._backups.pop(i)
                    self._save(); return True
            return False

    def register_device(self, device_id: str, auto_sync: bool = True, sync_interval: float = 3600.0) -> None:
        with self._lock:
            self._sync_states[device_id] = SyncState(
                device_id=device_id, last_sync=0, modules_synced=[],
                auto_sync=auto_sync, sync_interval=sync_interval
            )
            self._save()

    def sync(self, target_device_id: str, modules: Optional[List[str]] = None, force: bool = False) -> Dict[str, Any]:
        """Sync memory modules to target device. Returns sync report."""
        with self._lock:
            modules = modules or self.BACKUP_MODULES
            if target_device_id not in self._sync_states:
                self.register_device(target_device_id)
            state = self._sync_states[target_device_id]
            now = time.time()
            if not force and now - state.last_sync < state.sync_interval:
                return {"synced": False, "reason": "Sync interval not elapsed", "next_sync": state.last_sync + state.sync_interval}
            # Create backup for sync
            backup = self.create_backup(modules, version="sync")
            # In production: upload to sync server, target device downloads
            # For now: store in shared sync directory
            sync_share = self.workspace / "sync" / target_device_id
            sync_share.mkdir(parents=True, exist_ok=True)
            archive_path = self.workspace / "archives" / f"{backup.id}.zip"
            sync_path = sync_share / f"{backup.id}.zip"
            shutil.copy2(archive_path, sync_path)
            state.last_sync = now
            state.modules_synced = modules
            state.conflict_count = 0
            self._save()
            return {"synced": True, "backup_id": backup.id, "modules": modules, "target": target_device_id, "timestamp": now}

    def receive_sync(self, device_id: str, backup_id: str, target_dirs: Optional[Dict[str, str]] = None) -> bool:
        """Receive a sync backup from another device."""
        sync_path = self.workspace / "sync" / device_id / f"{backup_id}.zip"
        if not sync_path.exists(): return False
        # Move to archives and restore
        archive_path = self.workspace / "archives" / f"{backup_id}.zip"
        shutil.copy2(sync_path, archive_path)
        # Create manifest from zip info
        with zipfile.ZipFile(archive_path, "r") as zf:
            modules = [name for name in zf.namelist() if "/" not in name]
        manifest = BackupManifest(
            id=backup_id, timestamp=time.time(), version="sync",
            source_device=device_id, memory_modules=modules,
            size_bytes=archive_path.stat().st_size
        )
        self._backups.append(manifest)
        return self.restore_backup(backup_id, target_dirs)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_backups = len(self._backups)
            total_size = sum(b.size_bytes for b in self._backups)
            total_devices = len(self._sync_states)
            return {
                "total_backups": total_backups,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "total_devices": total_devices,
                "devices": list(self._sync_states.keys()),
                "latest_backup": self._backups[-1].id if self._backups else None,
            }

    def print_summary(self) -> str:
        stats = self.get_stats()
        lines = [
            "=== Memory Backup & Sync Summary ===",
            f"Total Backups: {stats['total_backups']}",
            f"Total Size: {stats['total_size_mb']} MB",
            f"Devices Registered: {stats['total_devices']}",
            f"Devices: {', '.join(stats['devices'])}",
            f"Latest Backup: {stats['latest_backup']}",
            "
--- Sync States ---",
        ]
        for did, state in self._sync_states.items():
            status = "auto" if state.auto_sync else "manual"
            last = time.ctime(state.last_sync) if state.last_sync else "never"
            lines.append(f"  {did}: {status}, last_sync={last}, modules={len(state.modules_synced)}")
        return "
".join(lines)

if __name__ == "__main__":
    sync = MemoryBackupSyncNative(device_id="device_alpha")
    sync.register_device("device_beta", auto_sync=True)
    manifest = sync.create_backup(["identity", "vector_memory"])
    print("Backup:", manifest.id)
    print(sync.print_summary())
