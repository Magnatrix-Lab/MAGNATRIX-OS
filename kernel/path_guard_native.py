#!/usr/bin/env python3
"""
kernel/path_guard_native.py
===========================
Layer 0 — Path Validation & Sanitization

Replaces raw open() with guarded file operations.
Prevents path traversal, null byte injection, and directory escape.
"""

from __future__ import annotations

import os
from typing import Any, List, Optional


class PathGuard:
    """Centralized file path validation."""

    _ALLOWED_ROOTS: List[str] = []

    @classmethod
    def configure(cls, roots: List[str]) -> None:
        cls._ALLOWED_ROOTS = [os.path.abspath(r) for r in roots]

    @classmethod
    def validate(cls, user_path: str, max_len: int = 4096) -> str:
        if not isinstance(user_path, str):
            raise ValueError("Path must be string")
        if len(user_path) > max_len:
            raise ValueError(f"Path too long (> {max_len})")
        if "\x00" in user_path:
            raise ValueError("Path contains null bytes")
        # Normalize and get absolute
        abs_path = os.path.abspath(os.path.normpath(user_path))
        # Check against allowed roots
        for root in cls._ALLOWED_ROOTS:
            if abs_path == root or abs_path.startswith(root + os.sep):
                return abs_path
        raise ValueError(f"Path outside allowed directories: {user_path}")

    @classmethod
    def open(cls, path: str, mode: str = "r", **kwargs) -> Any:
        safe_path = cls.validate(path)
        return open(safe_path, mode, **kwargs)

    @classmethod
    def exists(cls, path: str) -> bool:
        try:
            return os.path.exists(cls.validate(path))
        except ValueError:
            return False

    @classmethod
    def mkdir(cls, path: str, mode: int = 0o777) -> None:
        safe_path = cls.validate(path)
        os.makedirs(safe_path, mode=mode, exist_ok=True)
