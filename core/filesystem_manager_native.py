#!/usr/bin/env python3
"""
File System Manager for MAGNATRIX-OS
Sandboxed file operations, path validation, access control,
atomic writes, and safe file traversal. Native stdlib only.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import os
import shutil
import stat
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class AccessLevel(enum.Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"


@dataclasses.dataclass
class FileRecord:
    path: str
    size: int
    modified_at: float
    created_at: float
    permissions: str
    checksum: str
    is_directory: bool = False


class FileSystemManager:
    """Sandboxed file manager with access control and safe operations."""

    def __init__(self, root_dir: str = "/tmp/magnatrix_fs") -> None:
        self.root = Path(root_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._allowed_paths: Set[str] = {str(self.root)}
        self._lock = threading.Lock()
        self._access_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Path validation
    # ------------------------------------------------------------------

    def _validate_path(self, path: str) -> Path:
        target = Path(path).resolve()
        for allowed in self._allowed_paths:
            if str(target).startswith(str(Path(allowed).resolve())):
                return target
        raise PermissionError(f"Path '{path}' outside allowed sandbox")

    def allow_path(self, path: str) -> None:
        self._allowed_paths.add(str(Path(path).resolve()))

    def remove_allowed_path(self, path: str) -> None:
        self._allowed_paths.discard(str(Path(path).resolve()))

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log_access(self, action: str, path: str, success: bool) -> None:
        self._access_log.append({
            "action": action,
            "path": path,
            "success": success,
            "timestamp": time.time(),
        })

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def read(self, path: str, mode: str = "r", encoding: str = "utf-8") -> Any:
        target = self._validate_path(path)
        try:
            if "b" in mode:
                data = target.read_bytes()
            else:
                data = target.read_text(encoding=encoding)
            self._log_access("read", path, True)
            return data
        except Exception as e:
            self._log_access("read", path, False)
            raise

    def write(self, path: str, content: Any, mode: str = "w", encoding: str = "utf-8", atomic: bool = True) -> None:
        target = self._validate_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            if atomic:
                fd, tmp_path = tempfile.mkstemp(dir=str(target.parent), suffix=".tmp")
                try:
                    if "b" in mode:
                        os.write(fd, content if isinstance(content, bytes) else str(content).encode())
                    else:
                        os.write(fd, str(content).encode(encoding))
                    os.close(fd)
                    shutil.move(tmp_path, str(target))
                except Exception:
                    os.close(fd)
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                    raise
            else:
                if "b" in mode:
                    target.write_bytes(content if isinstance(content, bytes) else str(content).encode())
                else:
                    target.write_text(str(content), encoding=encoding)
            self._log_access("write", path, True)
        except Exception as e:
            self._log_access("write", path, False)
            raise

    def delete(self, path: str) -> bool:
        target = self._validate_path(path)
        try:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            self._log_access("delete", path, True)
            return True
        except Exception:
            self._log_access("delete", path, False)
            return False

    def copy(self, src: str, dst: str) -> None:
        src_path = self._validate_path(src)
        dst_path = self._validate_path(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        if src_path.is_dir():
            shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
        else:
            shutil.copy2(src_path, dst_path)
        self._log_access("copy", f"{src} -> {dst}", True)

    def move(self, src: str, dst: str) -> None:
        src_path = self._validate_path(src)
        dst_path = self._validate_path(dst)
        shutil.move(str(src_path), str(dst_path))
        self._log_access("move", f"{src} -> {dst}", True)

    def list_dir(self, path: str = ".") -> List[FileRecord]:
        target = self._validate_path(path)
        results = []
        for item in target.iterdir():
            try:
                info = item.stat()
                perms = stat.filemode(info.st_mode)
                checksum = ""
                if item.is_file():
                    checksum = hashlib.sha256(item.read_bytes()).hexdigest()[:16]
                results.append(FileRecord(
                    path=str(item.relative_to(self.root)),
                    size=info.st_size,
                    modified_at=info.st_mtime,
                    created_at=info.st_ctime,
                    permissions=perms,
                    checksum=checksum,
                    is_directory=item.is_dir(),
                ))
            except Exception:
                pass
        return results

    def exists(self, path: str) -> bool:
        try:
            target = self._validate_path(path)
            return target.exists()
        except PermissionError:
            return False

    def is_file(self, path: str) -> bool:
        try:
            return self._validate_path(path).is_file()
        except PermissionError:
            return False

    def is_dir(self, path: str) -> bool:
        try:
            return self._validate_path(path).is_dir()
        except PermissionError:
            return False

    def mkdir(self, path: str, parents: bool = True) -> None:
        target = self._validate_path(path)
        target.mkdir(parents=parents, exist_ok=True)
        self._log_access("mkdir", path, True)

    def rmdir(self, path: str) -> bool:
        target = self._validate_path(path)
        try:
            if target.is_dir():
                shutil.rmtree(target)
                self._log_access("rmdir", path, True)
                return True
        except Exception:
            self._log_access("rmdir", path, False)
        return False

    def get_checksum(self, path: str) -> str:
        target = self._validate_path(path)
        return hashlib.sha256(target.read_bytes()).hexdigest()

    def get_size(self, path: str) -> int:
        target = self._validate_path(path)
        return target.stat().st_size if target.exists() else 0

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def find(self, pattern: str, start_dir: str = ".", max_depth: int = 10) -> List[str]:
        target = self._validate_path(start_dir)
        results = []
        for root, dirs, files in os.walk(target):
            depth = len(Path(root).relative_to(target).parts)
            if depth > max_depth:
                del dirs[:]
                continue
            for name in files + dirs:
                if pattern in name:
                    results.append(str(Path(root) / name))
        return results

    def grep(self, keyword: str, start_dir: str = ".", extensions: Optional[List[str]] = None) -> List[Tuple[str, int, str]]:
        target = self._validate_path(start_dir)
        results = []
        for root, _, files in os.walk(target):
            for f in files:
                if extensions and not any(f.endswith(ext) for ext in extensions):
                    continue
                path = Path(root) / f
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                    for i, line in enumerate(text.split("\n"), 1):
                        if keyword in line:
                            results.append((str(path), i, line.strip()))
                except Exception:
                    pass
        return results

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        total_size = 0
        file_count = 0
        dir_count = 0
        for root, dirs, files in os.walk(self.root):
            dir_count += len(dirs)
            for f in files:
                try:
                    total_size += (Path(root) / f).stat().st_size
                    file_count += 1
                except Exception:
                    pass
        return {
            "root": str(self.root),
            "allowed_paths": len(self._allowed_paths),
            "files": file_count,
            "directories": dir_count,
            "total_size": total_size,
            "access_log_entries": len(self._access_log),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    import tempfile
    tmp = tempfile.mkdtemp(prefix="magnatrix_fs_")
    fs = FileSystemManager(tmp)
    print("=== File System Manager Demo ===\n")
    # Write
    fs.write("hello.txt", "Hello, MAGNATRIX-OS!")
    fs.write("nested/dir/data.json", json.dumps({"key": "value"}))
    # Read
    print(f"Read hello.txt: {fs.read('hello.txt')}")
    # List
    print(f"\nList root:")
    for rec in fs.list_dir():
        print(f"  {rec.path} ({'dir' if rec.is_directory else rec.size} bytes)")
    # Search
    print(f"\nFind 'hello': {fs.find('hello')}")
    # Checksum
    print(f"Checksum: {fs.get_checksum('hello.txt')[:16]}...")
    # Stats
    print(f"\nStats: {fs.stats()}")
    # Cleanup
    shutil.rmtree(tmp)
    print("\nCleanup complete.")


if __name__ == "__main__":
    _demo()
