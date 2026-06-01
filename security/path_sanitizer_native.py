"""security/path_sanitizer_native.py — Path sanitization wrapper"""
from __future__ import annotations
import os
import threading
from typing import Optional

class PathSanitizer:
    """Sanitize paths to prevent directory traversal."""

    def __init__(self, base_dir: str = "."):
        self.base_dir = os.path.abspath(base_dir)
        self._lock = threading.Lock()
        self._access_log: list = []

    def sanitize(self, path: str, base_dir: Optional[str] = None) -> str:
        """Sanitize path, reject traversal attempts."""
        base = os.path.abspath(base_dir or self.base_dir)

        if os.path.isabs(path):
            abs_path = os.path.abspath(path)
        else:
            abs_path = os.path.abspath(os.path.join(base, path))

        # Check traversal
        if not abs_path.startswith(base + os.sep) and abs_path != base:
            raise ValueError(f"Path traversal blocked: {path}")

        # Check for .. components
        normalized = os.path.normpath(abs_path)
        if ".." in path.split(os.sep):
            raise ValueError(f"Path contains parent reference: {path}")

        with self._lock:
            self._access_log.append({"path": abs_path, "allowed": True})

        return normalized

    def open_safe(self, path: str, mode: str = "r", base_dir: Optional[str] = None):
        """Safely open a file."""
        safe_path = self.sanitize(path, base_dir)
        return open(safe_path, mode)

    def exists_safe(self, path: str, base_dir: Optional[str] = None) -> bool:
        try:
            safe_path = self.sanitize(path, base_dir)
            return os.path.exists(safe_path)
        except ValueError:
            return False

    def mkdir_safe(self, path: str, base_dir: Optional[str] = None) -> None:
        safe_path = self.sanitize(path, base_dir)
        os.makedirs(safe_path, exist_ok=True)

if __name__ == "__main__":
    print("PathSanitizer self-test")
    ps = PathSanitizer()
    assert ps.sanitize("test.txt") != ""
    try:
        ps.sanitize("../etc/passwd")
        assert False
    except ValueError:
        pass
    print("All tests pass")
