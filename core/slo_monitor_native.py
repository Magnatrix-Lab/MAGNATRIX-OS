#!/usr/bin/env python3
"""SLO Monitor for MAGNATRIX-OS — Service Level Objective tracking."""
from __future__ import annotations
import time
from typing import Any, Dict, List

class SLIMonitor:
    def __init__(self) -> None:
        self._slos: Dict[str, Dict[str, Any]] = {}

    def define_slo(self, name: str, target: float, metric: str = "availability") -> None:
        self._slos[name] = {"target": target, "metric": metric, "measurements": [], "breaches": 0}

    def record(self, name: str, value: float) -> None:
        slo = self._slos.get(name)
        if slo:
            slo["measurements"].append(value)
            if len(slo["measurements"]) > 1000:
                slo["measurements"] = slo["measurements"][-500:]
            if value < slo["target"]:
                slo["breaches"] += 1

    def status(self, name: str) -> Dict[str, Any]:
        slo = self._slos.get(name)
        if not slo:
            return {"error": "SLO not found"}
        vals = slo["measurements"]
        return {
            "target": slo["target"],
            "current": sum(vals) / len(vals) if vals else 0,
            "breaches": slo["breaches"],
            "status": "OK" if (sum(vals) / len(vals) >= slo["target"] if vals else True) else "BREACH",
        }

    def stats(self) -> Dict[str, Any]:
        return {"slos": len(self._slos)}
