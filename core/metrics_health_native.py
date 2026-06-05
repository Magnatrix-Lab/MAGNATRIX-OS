"""
Metrics & Health Dashboard — MAGNATRIX-OS Core
System health checks, Prometheus-style metrics, uptime monitoring.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from __future__ import annotations

import time, os, json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class HealthCheck:
    """Single health check result."""
    component: str
    status: str  # healthy, degraded, unhealthy, unknown
    latency_ms: float
    message: str
    last_check: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "message": self.message,
            "last_check": self.last_check,
        }


class MetricsCollector:
    """Collect metrics in Prometheus-style format."""

    def __init__(self) -> None:
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._timestamps: Dict[str, float] = {}

    def counter(self, name: str, value: float = 1.0) -> None:
        self._counters[name] = self._counters.get(name, 0) + value
        self._timestamps[name] = time.time()

    def gauge(self, name: str, value: float) -> None:
        self._gauges[name] = value
        self._timestamps[name] = time.time()

    def histogram(self, name: str, value: float) -> None:
        if name not in self._histograms:
            self._histograms[name] = []
        self._histograms[name].append(value)
        self._timestamps[name] = time.time()

    def get_prometheus_format(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []
        for name, value in self._counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        for name, value in self._gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        for name, values in self._histograms.items():
            if values:
                lines.append(f"# TYPE {name} histogram")
                lines.append(f"{name}_count {len(values)}")
                lines.append(f"{name}_sum {sum(values)}")
                lines.append(f"{name}_avg {sum(values) / len(values)}")
        return "\n".join(lines)

    def get_json(self) -> Dict[str, Any]:
        return {
            "counters": self._counters,
            "gauges": self._gauges,
            "histograms": {k: {"count": len(v), "sum": sum(v), "avg": sum(v) / len(v)} for k, v in self._histograms.items()},
            "timestamp": time.time(),
        }


class HealthDashboard:
    """System health monitoring dashboard."""

    def __init__(self) -> None:
        self._checks: Dict[str, HealthCheck] = {}
        self._metrics = MetricsCollector()
        self._start_time = time.time()

    def check(self, component: str, check_fn: callable) -> HealthCheck:
        """Run a health check on a component."""
        start = time.time()
        try:
            result = check_fn()
            latency = (time.time() - start) * 1000
            status = "healthy" if result else "degraded"
            message = "OK" if result else "Degraded"
        except Exception as e:
            latency = (time.time() - start) * 1000
            status = "unhealthy"
            message = str(e)

        check = HealthCheck(component, status, latency, message, time.time())
        self._checks[component] = check
        self._metrics.counter(f"healthcheck_total", 1)
        self._metrics.gauge(f"healthcheck_latency_{component}", latency)
        return check

    def get_overall_status(self) -> str:
        statuses = [c.status for c in self._checks.values()]
        if "unhealthy" in statuses:
            return "unhealthy"
        elif "degraded" in statuses:
            return "degraded"
        elif not statuses:
            return "unknown"
        return "healthy"

    def get_checks(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self._checks.values()]

    def uptime_seconds(self) -> float:
        return time.time() - self._start_time

    def get_dashboard(self) -> Dict[str, Any]:
        return {
            "overall_status": self.get_overall_status(),
            "uptime_seconds": self.uptime_seconds(),
            "checks": self.get_checks(),
            "metrics": self._metrics.get_json(),
            "timestamp": time.time(),
        }

    def export_prometheus(self) -> str:
        return self._metrics.get_prometheus_format()


def run():
    print("=" * 60)
    print("Metrics & Health Dashboard — Demo")
    print("=" * 60)

    dashboard = HealthDashboard()

    print("\n[1] Health checks")
    dashboard.check("policy_engine", lambda: True)
    dashboard.check("audit_trail", lambda: True)
    dashboard.check("model_router", lambda: False)  # Simulated failure
    dashboard.check("database", lambda: (_ for _ in ()).throw(RuntimeError("Connection refused")))

    for c in dashboard.get_checks():
        print(f"   {c['component']}: {c['status']} ({c['latency_ms']:.1f}ms) — {c['message']}")

    print(f"\n[2] Overall: {dashboard.get_overall_status()}")
    print(f"   Uptime: {dashboard.uptime_seconds():.1f}s")

    print("\n[3] Prometheus metrics")
    print(dashboard.export_prometheus()[:300])

    print("\n[4] Full dashboard")
    print(f"   Keys: {list(dashboard.get_dashboard().keys())}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
