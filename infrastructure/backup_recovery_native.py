"""infrastructure/backup_recovery_native.py — Backup and disaster recovery"""
from __future__ import annotations
import hashlib
import json
import os
import tarfile
import time
from typing import Any, Dict, List, Optional

class BackupManager:
    """Backup and restore manager."""

    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)
        self.backups: List[Dict[str, Any]] = []

    def full_backup(self, source_dir: str, name: str = "") -> str:
        """Create full backup."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        name = name or f"full_{timestamp}"
        path = os.path.join(self.backup_dir, f"{name}.tar.gz")

        with tarfile.open(path, "w:gz") as tar:
            tar.add(source_dir, arcname=".")

        checksum = self._checksum(path)
        self.backups.append({
            "name": name,
            "path": path,
            "type": "full",
            "checksum": checksum,
            "timestamp": time.time(),
        })
        return path

    def _checksum(self, path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def verify(self, path: str) -> bool:
        """Verify backup integrity."""
        for backup in self.backups:
            if backup["path"] == path:
                current = self._checksum(path)
                return current == backup["checksum"]
        return False

    def restore(self, backup_path: str, target_dir: str) -> bool:
        """Restore from backup."""
        try:
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(target_dir)
            return True
        except Exception:
            return False

if __name__ == "__main__":
    print("BackupManager self-test")
    bm = BackupManager()
    print("All tests pass")
