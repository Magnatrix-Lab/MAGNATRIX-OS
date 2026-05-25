#!/usr/bin/env python3
"""
kernel/health_aggregator_native.py
==================================
Layer 0 — Health Check Aggregation

Aggregates health status from all layers into a single /healthz response.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class HealthCheck:
    name: str
    check_fn: Callable[[], tuple[bool, str]]
    critical: bool = False  # If True, overall health = False when this fails


class HealthAggregator:
    """Aggregate health checks from all MAGNATRIX layers."""

    def __init__(self) -> None:
        self._checks: List[HealthCheck] = []

    def register(self, name: str, check_fn: Callable[[], tuple[bool, str]],
                 critical: bool = False) -> None:
        self._checks.append(HealthCheck(name, check_fn, critical))

    def check_all(self) -> Dict:
        results = {}
        overall = True
        for hc in self._checks:
            ok, msg = hc.check_fn()
            results[hc.name] = {"healthy": ok, "message": msg}
            if hc.critical and not ok:
                overall = False
        return {
            "healthy": overall,
            "timestamp": time.time(),
            "checks": results,
            "total": len(self._checks),
            "passed": sum(1 for r in results.values() if r["healthy"]),
        }

    def healthz_response(self) -> str:
        result = self.check_all()
        status = "healthy" if result["healthy"] else "unhealthy"
        return f"STATUS: {status}\nPASSED: {result['passed']}/{result['total']}\n"


def demo() -> None:
    agg = HealthAggregator()
    agg.register("kernel", lambda: (True, "OK"), critical=True)
    agg.register("crypto", lambda: (True, "Ed25519 verified"))
    agg.register("sandbox", lambda: (False, "seccomp not active"), critical=True)
    print(agg.check_all())


if __name__ == "__main__":
    demo()
