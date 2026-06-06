#!/usr/bin/env python3
"""
Health Check Aggregator for MAGNATRIX-OS
Aggregates health status from all modules, provides a unified
dashboard, and triggers alerts on degradation. Native stdlib only.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import json
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class HealthStatus(enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclasses.dataclass
class HealthReport:
    module_name: str
    status: HealthStatus
    latency_ms: float
    message: str
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)
    timestamp: float = dataclasses.field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module": self.module_name,
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "message": self.message,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class HealthCheckAggregator:
    """Aggregates health checks across all MAGNATRIX-OS modules."""

    def __init__(self) -> None:
        self._checks: Dict[str, Callable[[], HealthReport]] = {}
        self._history: List[Dict[str, Any]] = []
        self._alerts: List[Dict[str, Any]] = []
        self._thresholds: Dict[str, HealthStatus] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, module_name: str, check_fn: Callable[[], HealthReport]) -> None:
        self._checks[module_name] = check_fn

    def set_threshold(self, module_name: str, threshold: HealthStatus) -> None:
        self._thresholds[module_name] = threshold

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def check(self, module_name: str) -> Optional[HealthReport]:
        fn = self._checks.get(module_name)
        if not fn:
            return HealthReport(module_name, HealthStatus.UNKNOWN, 0, "No check registered")
        start = time.perf_counter()
        try:
            report = fn()
            report.latency_ms = (time.perf_counter() - start) * 1000
        except Exception as e:
            report = HealthReport(module_name, HealthStatus.UNHEALTHY, (time.perf_counter() - start) * 1000, str(e))
        self._history.append(report.to_dict())
        # Check threshold
        threshold = self._thresholds.get(module_name, HealthStatus.UNHEALTHY)
        if self._status_worse(report.status, threshold):
            self._alerts.append({
                "timestamp": time.time(),
                "module": module_name,
                "status": report.status.value,
                "message": report.message,
            })
        return report

    def check_all(self) -> Dict[str, HealthReport]:
        results = {}
        for name in self._checks:
            results[name] = self.check(name)
        return results

    def _status_worse(self, actual: HealthStatus, threshold: HealthStatus) -> bool:
        order = {HealthStatus.HEALTHY: 0, HealthStatus.DEGRADED: 1, HealthStatus.UNKNOWN: 2, HealthStatus.UNHEALTHY: 3}
        return order.get(actual, 2) > order.get(threshold, 1)

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def dashboard(self) -> Dict[str, Any]:
        all_checks = self.check_all()
        by_status = {}
        for report in all_checks.values():
            by_status[report.status.value] = by_status.get(report.status.value, 0) + 1
        total_latency = sum(r.latency_ms for r in all_checks.values())
        return {
            "overall": self._overall_status(all_checks),
            "modules": {k: v.to_dict() for k, v in all_checks.items()},
            "by_status": by_status,
            "total_latency_ms": round(total_latency, 2),
            "timestamp": time.time(),
        }

    def _overall_status(self, checks: Dict[str, HealthReport]) -> str:
        statuses = [r.status for r in checks.values()]
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY.value
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED.value
        if HealthStatus.UNKNOWN in statuses:
            return HealthStatus.UNKNOWN.value
        return HealthStatus.HEALTHY.value

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_history(self, module_name: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        filtered = self._history
        if module_name:
            filtered = [h for h in filtered if h.get("module") == module_name]
        return filtered[-limit:]

    def get_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._alerts[-limit:]

    def clear_alerts(self) -> None:
        self._alerts.clear()

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        return {
            "registered_checks": len(self._checks),
            "history_entries": len(self._history),
            "alerts": len(self._alerts),
            "thresholds": len(self._thresholds),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    agg = HealthCheckAggregator()
    print("=== Health Check Aggregator Demo ===\n")
    # Register mock checks
    def check_cpu() -> HealthReport:
        return HealthReport("cpu", HealthStatus.HEALTHY, 0.5, "CPU usage normal", {"usage": 45})
    def check_memory() -> HealthReport:
        return HealthReport("memory", HealthStatus.DEGRADED, 1.2, "Memory usage high", {"usage": 85})
    def check_disk() -> HealthReport:
        return HealthReport("disk", HealthStatus.HEALTHY, 0.3, "Disk OK", {"usage": 30})
    agg.register("cpu", check_cpu)
    agg.register("memory", check_memory)
    agg.register("disk", check_disk)
    agg.set_threshold("memory", HealthStatus.DEGRADED)
    # Run checks
    dash = agg.dashboard()
    print(f"Overall: {dash['overall']}")
    print(f"By status: {dash['by_status']}")
    print(f"Alerts: {len(agg.get_alerts())}")
    print(f"Stats: {agg.stats()}")


if __name__ == "__main__":
    _demo()
