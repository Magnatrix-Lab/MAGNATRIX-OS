#!/usr/bin/env python3
"""
kernel/api_versioning_native.py
===============================
Layer 0 — API Versioning for Kernel Bridge

Provides backward-compatible RPC dispatch with version negotiation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


@dataclass
class APIVersion:
    major: int = 0
    minor: int = 7
    patch: int = 1

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def compatible_with(self, other: "APIVersion") -> bool:
        return self.major == other.major and self.minor >= other.minor


class VersionedHandler:
    """Decorator for versioned API handlers."""

    def __init__(self) -> None:
        self._handlers: Dict[str, Dict[str, Callable]] = {}  # action -> version -> fn

    def register(self, action: str, version: str, fn: Callable) -> None:
        if action not in self._handlers:
            self._handlers[action] = {}
        self._handlers[action][version] = fn

    def dispatch(self, action: str, version: str, **kwargs) -> Any:
        versions = self._handlers.get(action, {})
        if version in versions:
            return versions[version](**kwargs)
        # Fallback: try latest compatible version
        for v in sorted(versions.keys(), reverse=True):
            if v.startswith(version.split(".")[0]):
                return versions[v](**kwargs)
        raise ValueError(f"No handler for {action}@{version}")


class VersionedKernelBridge:
    """Kernel bridge with API versioning."""

    CURRENT_VERSION = APIVersion(0, 7, 1)

    def __init__(self) -> None:
        self._handler = VersionedHandler()

    def register(self, action: str, fn: Callable, since: str = "0.7.0") -> None:
        self._handler.register(action, since, fn)

    def handle(self, action: str, version: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        v = version or str(self.CURRENT_VERSION)
        try:
            result = self._handler.dispatch(action, v, **kwargs)
            return {"ok": True, "version": v, "result": result}
        except Exception as e:
            return {"ok": False, "version": v, "error": str(e)}
