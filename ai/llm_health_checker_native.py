"""LLM Health Checker — Native Python (stdlib only)."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class HealthStatus(Enum):
    HEALTHY = auto()
    DEGRADED = auto()
    UNHEALTHY = auto()
    UNKNOWN = auto()

@dataclass
class HealthCheck:
    id: str
    name: str
    check_fn: Callable[[], tuple]
    interval: float = 60.0
    last_run: float = 0.0
    status: HealthStatus = HealthStatus.UNKNOWN
    message: str = ""

class HealthChecker:
    def __init__(self) -> None:
        self._checks: Dict[str, HealthCheck] = {}

    def register(self, check: HealthCheck) -> None:
        self._checks[check.id] = check

    def run(self, check_id: str) -> HealthStatus:
        check = self._checks.get(check_id)
        if not check:
            return HealthStatus.UNKNOWN
        check.last_run = time.time()
        try:
            status, message = check.check_fn()
            check.status = status
            check.message = message
        except Exception as ex:
            check.status = HealthStatus.UNHEALTHY
            check.message = str(ex)
        return check.status

    def run_all(self) -> Dict[str, HealthStatus]:
        return {cid: self.run(cid) for cid in self._checks}

    def is_healthy(self) -> bool:
        return all(c.status == HealthStatus.HEALTHY for c in self._checks.values())

    def get_degraded(self) -> List[str]:
        return [c.id for c in self._checks.values() if c.status == HealthStatus.DEGRADED]

    def get_stats(self) -> Dict[str, Any]:
        counts = {}
        for c in self._checks.values():
            counts[c.status.name] = counts.get(c.status.name, 0) + 1
        return {"checks": len(self._checks), "by_status": counts, "healthy": self.is_healthy()}

def run() -> None:
    print("Health Checker test")
    e = HealthChecker()
    e.register(HealthCheck("h1", "database", lambda: (HealthStatus.HEALTHY, "Connected"), 30.0))
    e.register(HealthCheck("h2", "cache", lambda: (HealthStatus.DEGRADED, "High latency"), 30.0))
    e.register(HealthCheck("h3", "api", lambda: (HealthStatus.HEALTHY, "OK"), 30.0))
    results = e.run_all()
    for cid, status in results.items():
        print("  " + cid + ": " + status.name)
    print("  Overall healthy: " + str(e.is_healthy()))
    print("  Degraded: " + str(e.get_degraded()))
    print("  Stats: " + str(e.get_stats()))
    print("Health Checker test complete.")

if __name__ == "__main__":
    run()
