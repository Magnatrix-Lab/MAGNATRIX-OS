#!/usr/bin/env python3
"""ClassLoader Monitor for MAGNATRIX-OS."""
from __future__ import annotations
import time
from typing import Any, Dict, List, Optional

class ClassLoaderMonitor:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.events: List[Dict[str, Any]] = []
        self._whitelist = set()
    def whitelist(self, module_name: str):
        self._whitelist.add(module_name)
    def on_load(self, module_name: str, source: str = "unknown"):
        if module_name in self._whitelist:
            return
        self.events.append({"module": module_name, "source": source, "timestamp": time.time(), "type": "class_load"})
    def detect_anomalies(self) -> List[Dict[str, Any]]:
        # Detect rapid loading or loading from unusual sources
        recent = [e for e in self.events if time.time() - e["timestamp"] < 60]
        if len(recent) > 10:
            return [{"type": "rapid_loading", "count": len(recent), "severity": "high"}]
        return []
    def to_dict(self): return {"events": len(self.events), "whitelist": len(self._whitelist)}
