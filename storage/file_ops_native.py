#!/usr/bin/env python3
"""
storage/file_ops_native.py
==========================
Layer 0 — Secure File Operations (PathGuard wrapper)

Drop-in replacement for open() that validates all paths before access.
All MAGNATRIX layers should import from here instead of using raw open().
"""

from __future__ import annotations

import os
import sys
from typing import Any, List

# Ensure PathGuard is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "kernel"))
from path_guard_native import PathGuard

# Default allowed roots for MAGNATRIX-OS
_DEFAULT_ROOTS: List[str] = [
    "/var/lib/magnatrix",
    "/tmp/magnatrix",
    "/mnt/agents/MAGNATRIX-OS",
]

PathGuard.configure(_DEFAULT_ROOTS)


def open(path: str, mode: str = "r", **kwargs) -> Any:
    """Secure open() — validates path before access."""
    return PathGuard.open(path, mode, **kwargs)


def exists(path: str) -> bool:
    return PathGuard.exists(path)


def mkdir(path: str, mode: int = 0o777) -> None:
    PathGuard.mkdir(path, mode)


# Re-export standard os.path functions (safe ones)
join = os.path.join
abspath = os.path.abspath
basename = os.path.basename
dirname = os.path.dirname
