"""Health Checker — probe system, dependency checks, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from enum import Enum, auto
import time

class HealthStatus(Enum):
    HEALTHY = auto()
    DEGRADED = auto()
    UNHEALTHY = auto()
    UNKNOWN = auto()

@dataclass
class HealthCheck:
    check_id: str
    name: str
    status: HealthStatus
    latency_ms: float
    message: str
    last_run: float

class HealthChecker:
    def __init__(self):
        self.checks: Dict[str, Callable[[], Dict]] = {}
        self.results: List[HealthCheck] = []
        self.dependencies: Dict[str, List[str]] = {}

    def register(self, check_id: str, name: str, check_fn: Callable[[], Dict], dependencies: List[str] = None):
        self.checks[check_id] = check_fn
        self.dependencies[check_id] = dependencies or []

    def run_check(self, check_id: str) -> HealthCheck:
        start = time.time()
        try:
            result = self.checks[check_id]()
            latency = (time.time() - start) * 1000
            status = HealthStatus[result.get("status", "UNKNOWN")]
            msg = result.get("message", "")
        except Exception as e:
            latency = (time.time() - start) * 1000
            status = HealthStatus.UNHEALTHY
            msg = str(e)
        check = HealthCheck(check_id, check_id, status, latency, msg, time.time())
        self.results.append(check)
        return check

    def run_all(self) -> Dict[str, HealthCheck]:
        results = {}
        for check_id in self.checks:
            results[check_id] = self.run_check(check_id)
        return results

    def overall_status(self) -> HealthStatus:
        if not self.results:
            return HealthStatus.UNKNOWN
        if any(r.status == HealthStatus.UNHEALTHY for r in self.results):
            return HealthStatus.UNHEALTHY
        if any(r.status == HealthStatus.DEGRADED for r in self.results):
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    def stats(self) -> Dict:
        statuses = {}
        for r in self.results:
            statuses[r.status.name] = statuses.get(r.status.name, 0) + 1
        return {"checks": len(self.checks), "overall": self.overall_status().name, "statuses": statuses}

def run():
    checker = HealthChecker()
    def db_check():
        return {"status": "HEALTHY", "message": "DB connected"}
    def api_check():
        return {"status": "DEGRADED", "message": "High latency"}
    checker.register("db", "Database", db_check)
    checker.register("api", "API", api_check)
    checker.run_all()
    print(checker.overall_status().name)
    print(checker.stats())

if __name__ == "__main__":
    run()
