#!/usr/bin/env python3
"""Canary Release for MAGNATRIX-OS — Gradual rollout."""
from __future__ import annotations
import hashlib, random
from typing import Any, Dict, List

class CanaryRelease:
    def __init__(self, version: str, traffic_percent: float = 10.0) -> None:
        self.version = version
        self.traffic_percent = traffic_percent
        self._users: List[str] = []

    def should_route(self, user_id: str) -> bool:
        h = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        return (h % 100) < self.traffic_percent

    def promote(self, new_percent: float) -> None:
        self.traffic_percent = min(100.0, new_percent)

    def stats(self) -> Dict[str, Any]:
        return {"version": self.version, "traffic_percent": self.traffic_percent}
