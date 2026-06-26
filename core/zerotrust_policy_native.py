#!/usr/bin/env python3
"""Zero-Trust Policy Engine for MAGNATRIX-OS — Network micro-segmentation."""
from __future__ import annotations
import time
from typing import Any, Dict, List, Optional

class ZeroTrustPolicy:
    def __init__(self) -> None:
        self._policies: List[Dict[str, Any]] = []

    def add_policy(self, source: str, dest: str, action: str, conditions: Optional[Dict[str, Any]] = None) -> None:
        self._policies.append({"source": source, "dest": dest, "action": action, "conditions": conditions or {}, "created": time.time()})

    def allow(self, source: str, dest: str, context: Optional[Dict[str, Any]] = None) -> bool:
        context = context or {}
        for p in self._policies:
            if p["source"] == source and p["dest"] == dest:
                if p["action"] == "allow":
                    return True
                elif p["action"] == "deny":
                    return False
        return False

    def stats(self) -> Dict[str, Any]:
        return {"policies": len(self._policies)}
