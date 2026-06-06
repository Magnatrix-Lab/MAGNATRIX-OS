#!/usr/bin/env python3
"""
Backup & Recovery for MAGNATRIX-OS
Automated backup, snapshot, incremental, restore verification.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tarfile
import time
from typing import Any, Dict, List, Optional


class BackupSnapshot:
    """Backup snapshot metadata."""

    def __init__(self, snapshot_id: str, path: str, size: int, checksum: str, timestamp: float) -> None:
        self.snapshot_id = snapshot_id
        self.path = path
        self.size = size
        self.checksum = checksum
        self.timestamp = timestamp
        self.type = 'full'


class BackupManager:
    """Backup and recovery manager."""

    def __init__(self, backup_dir: str = './backups') -> None:
        self._backup_dir = backup_dir
        self._snapshots: List[BackupSnapshot] = []
        os.makedirs(backup_dir, exist_ok=True)

    def full_backup(self, source_dir: str, name: Optional[str] = None) -> BackupSnapshot:
        """Create full backup of directory."""
        snapshot_id = name or f"backup_{int(time.time())}"
        backup_path = os.path.join(self._backup_dir, f"{snapshot_id}.tar.gz")

        # Create tar.gz archive
        with tarfile.open(backup_path, 'w:gz') as tar:
            tar.add(source_dir, arcname=os.path.basename(source_dir))

        size = os.path.getsize(backup_path)
        checksum = self._file_checksum(backup_path)

        snapshot = BackupSnapshot(snapshot_id, backup_path, size, checksum, time.time())
        self._snapshots.append(snapshot)
        self._save_index()
        return snapshot

    def incremental_backup(self, source_dir: str, base_snapshot: str) -> BackupSnapshot:
        """Create incremental backup (only files changed since base)."""
        snapshot_id = f"inc_{int(time.time())}"
        backup_path = os.path.join(self._backup_dir, f"{snapshot_id}.tar.gz")

        # Find changed files (simplified: files modified since last backup)
        base_time = 0
        for s in self._snapshots:
            if s.snapshot_id == base_snapshot:
                base_time = s.timestamp
                break

        changed_files = []
        for root, _, files in os.walk(source_dir):
            for f in files:
                path = os.path.join(root, f)
                if os.path.getmtime(path) > base_time:
                    changed_files.append(path)

        with tarfile.open(backup_path, 'w:gz') as tar:
            for f in changed_files:
                tar.add(f, arcname=os.path.relpath(f, source_dir))

        size = os.path.getsize(backup_path)
        checksum = self._file_checksum(backup_path)

        snapshot = BackupSnapshot(snapshot_id, backup_path, size, checksum, time.time())
        snapshot.type = 'incremental'
        self._snapshots.append(snapshot)
        self._save_index()
        return snapshot

    def restore(self, snapshot_id: str, target_dir: str) -> bool:
        """Restore from snapshot."""
        snapshot = next((s for s in self._snapshots if s.snapshot_id == snapshot_id), None)
        if not snapshot or not os.path.exists(snapshot.path):
            return False

        os.makedirs(target_dir, exist_ok=True)
        with tarfile.open(snapshot.path, 'r:gz') as tar:
            tar.extractall(target_dir)

        # Verify
        return self._verify_restore(snapshot, target_dir)

    def _verify_restore(self, snapshot: BackupSnapshot, target_dir: str) -> bool:
        # Simplified: check if directory exists and is not empty
        if not os.path.exists(target_dir):
            return False
        return len(os.listdir(target_dir)) > 0

    def _file_checksum(self, path: str) -> str:
        sha256 = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def list_snapshots(self) -> List[Dict[str, Any]]:
        return [
            {
                'id': s.snapshot_id,
                'type': s.type,
                'size': s.size,
                'checksum': s.checksum[:16] + '...',
                'timestamp': time.ctime(s.timestamp),
            }
            for s in self._snapshots
        ]

    def _save_index(self) -> None:
        index = [
            {
                'id': s.snapshot_id,
                'path': s.path,
                'size': s.size,
                'checksum': s.checksum,
                'timestamp': s.timestamp,
                'type': s.type,
            }
            for s in self._snapshots
        ]
        with open(os.path.join(self._backup_dir, 'index.json'), 'w') as f:
            json.dump(index, f, indent=2)

    def delete_old(self, max_age_days: int = 30) -> int:
        cutoff = time.time() - (max_age_days * 86400)
        to_remove = [s for s in self._snapshots if s.timestamp < cutoff]
        for s in to_remove:
            if os.path.exists(s.path):
                os.remove(s.path)
            self._snapshots.remove(s)
        self._save_index()
        return len(to_remove)


def _demo() -> None:
    print("=== Backup & Recovery Demo ===\n")

    backup = BackupManager('/tmp/magnatrix_backups')

    # Create test directory
    os.makedirs('/tmp/test_source', exist_ok=True)
    with open('/tmp/test_source/file1.txt', 'w') as f:
        f.write('Hello World')
    with open('/tmp/test_source/file2.txt', 'w') as f:
        f.write('Test data')

    # Full backup
    snap1 = backup.full_backup('/tmp/test_source', 'full_backup_1')
    print(f"Full backup: {snap1.snapshot_id}, {snap1.size} bytes")

    # Modify and incremental backup
    with open('/tmp/test_source/file3.txt', 'w') as f:
        f.write('New data')
    snap2 = backup.incremental_backup('/tmp/test_source', 'full_backup_1')
    print(f"Incremental backup: {snap2.snapshot_id}, {snap2.size} bytes")

    # List snapshots
    print(f"Snapshots: {len(backup.list_snapshots())}")

    # Restore
    os.makedirs('/tmp/test_restore', exist_ok=True)
    success = backup.restore('full_backup_1', '/tmp/test_restore')
    print(f"Restore success: {success}")

    print("\n=== Backup & Recovery Demo Complete ===")


if __name__ == '__main__':
    _demo()
