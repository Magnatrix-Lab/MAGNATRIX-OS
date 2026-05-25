#!/usr/bin/env python3
"""
kernel/log_rotator_native.py
============================
Layer 0 — Log Rotation Engine

Provides:
  - Size-based rotation (default 100MB)
  - Time-based rotation (daily)
  - Gzip compression for archived logs
  - Max archive retention (default 30 files)
"""

from __future__ import annotations

import gzip
import os
import shutil
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class RotationConfig:
    max_bytes: int = 100 * 1024 * 1024  # 100MB
    backup_count: int = 30
    compress: bool = True
    rotate_by_time: bool = False  # If True, rotate daily


class LogRotator:
    """Rotate log files by size or time."""

    def __init__(self, filepath: str, config: Optional[RotationConfig] = None) -> None:
        self.filepath = filepath
        self.config = config or RotationConfig()
        self._last_rotation = 0

    def should_rotate(self) -> bool:
        if not os.path.exists(self.filepath):
            return False
        if self.config.rotate_by_time:
            # Check if day changed
            mtime = os.path.getmtime(self.filepath)
            return time.localtime(mtime).tm_yday != time.localtime().tm_yday
        return os.path.getsize(self.filepath) >= self.config.max_bytes

    def rotate(self) -> None:
        if not self.should_rotate():
            return
        # Rename existing backups: log.4.gz -> log.5.gz, etc.
        for i in range(self.config.backup_count - 1, 0, -1):
            src = f"{self.filepath}.{i}.gz"
            dst = f"{self.filepath}.{i + 1}.gz"
            if os.path.exists(src):
                if i + 1 >= self.config.backup_count:
                    os.remove(src)
                else:
                    shutil.move(src, dst)
        # Compress current log to .1.gz
        if os.path.exists(self.filepath):
            dst = f"{self.filepath}.1.gz"
            with open(self.filepath, "rb") as f_in:
                with gzip.open(dst, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            # Truncate current log
            with open(self.filepath, "w") as f:
                pass
        self._last_rotation = time.time()

    def write(self, data: str) -> None:
        self.rotate()
        with open(self.filepath, "a") as f:
            f.write(data)


def demo() -> None:
    import tempfile
    log_path = os.path.join(tempfile.mkdtemp(), "test.log")
    rot = LogRotator(log_path, RotationConfig(max_bytes=100, backup_count=3))
    for i in range(10):
        rot.write(f"Line {i}\n" * 20)
    print(f"Log files: {os.listdir(os.path.dirname(log_path))}")


if __name__ == "__main__":
    demo()
