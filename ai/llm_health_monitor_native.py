"""Health Monitor — System health checks, probe system, and degradation detection.

Modul ini menyediakan:
- HealthProbe untuk individual health checks
- HealthMonitor untuk aggregate health status
- DegradationDetector untuk detect performance degradation
- ProbeScheduler untuk schedule periodic health checks
- HealthReporter untuk generate health reports
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ProbeType(Enum):
    HTTP = auto()
    CUSTOM = auto()
    MEMORY = auto()
    CPU = auto()
    DISK = auto()
    LATENCY = auto()
    ERROR_RATE = auto()


@dataclass
class HealthProbe:
    """Single health probe definition."""
    probe_id: str
    name: str
    probe_type: ProbeType
    check_fn: Callable[[], Tuple[bool, float, str]]  # (success, latency_ms, message)
    interval: float = 60.0
    timeout: float = 5.0
    healthy_threshold: int = 2
    unhealthy_threshold: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProbeResult:
    """Result of a single probe execution."""
    probe_id: str
    success: bool
    latency_ms: float
    message: str
    timestamp: float
    status: HealthStatus
    consecutive_success: int = 0
    consecutive_failure: int = 0


class ProbeScheduler:
    """Schedule and execute periodic health checks."""

    def __init__(self):
        self._probes: Dict[str, HealthProbe] = {}
        self._last_run: Dict[str, float] = {}
        self._results: Dict[str, List[ProbeResult]] = {}

    def register(self, probe: HealthProbe) -> None:
        self._probes[probe.probe_id] = probe
        self._results[probe.probe_id] = []

    def run_probe(self, probe_id: str) -> Optional[ProbeResult]:
        probe = self._probes.get(probe_id)
        if not probe:
            return None
        start = time.time()
        try:
            success, latency, message = probe.check_fn()
        except Exception as e:
            success = False
            latency = (time.time() - start) * 1000
            message = str(e)

        # Determine status based on consecutive results
        prev_results = self._results.get(probe_id, [])
        consec_success = prev_results[-1].consecutive_success + 1 if prev_results and prev_results[-1].success else (1 if success else 0)
        consec_failure = prev_results[-1].consecutive_failure + 1 if prev_results and not prev_results[-1].success else (1 if not success else 0)

        if success and consec_success >= probe.healthy_threshold:
            status = HealthStatus.HEALTHY
        elif not success and consec_failure >= probe.unhealthy_threshold:
            status = HealthStatus.UNHEALTHY
        else:
            status = HealthStatus.DEGRADED

        result = ProbeResult(
            probe_id=probe_id,
            success=success,
            latency_ms=latency,
            message=message,
            timestamp=time.time(),
            status=status,
            consecutive_success=consec_success,
            consecutive_failure=consec_failure,
        )
        self._results[probe_id].append(result)
        # Keep last 100 results
        if len(self._results[probe_id]) > 100:
            self._results[probe_id] = self._results[probe_id][-100:]
        self._last_run[probe_id] = time.time()
        return result

    def run_all(self) -> Dict[str, ProbeResult]:
        results = {}
        for probe_id in self._probes:
            results[probe_id] = self.run_probe(probe_id)
        return results

    def run_due(self) -> Dict[str, ProbeResult]:
        now = time.time()
        results = {}
        for probe_id, probe in self._probes.items():
            last = self._last_run.get(probe_id, 0)
            if now - last >= probe.interval:
                results[probe_id] = self.run_probe(probe_id)
        return results

    def get_results(self, probe_id: str) -> List[ProbeResult]:
        return self._results.get(probe_id, [])

    def get_latest(self, probe_id: str) -> Optional[ProbeResult]:
        results = self._results.get(probe_id, [])
        return results[-1] if results else None


class DegradationDetector:
    """Detect performance degradation trends."""

    def __init__(self, latency_threshold: float = 1000.0, error_rate_threshold: float = 0.1):
        self.latency_threshold = latency_threshold
        self.error_rate_threshold = error_rate_threshold

    def analyze(self, results: List[ProbeResult]) -> Dict[str, Any]:
        if not results:
            return {"status": HealthStatus.UNKNOWN.name, "issues": []}

        recent = results[-10:]
        avg_latency = sum(r.latency_ms for r in recent) / len(recent)
        error_rate = sum(1 for r in recent if not r.success) / len(recent)
        latency_trend = recent[-1].latency_ms - recent[0].latency_ms if len(recent) > 1 else 0

        issues = []
        if avg_latency > self.latency_threshold:
            issues.append(f"High latency: {avg_latency:.1f}ms > {self.latency_threshold}ms")
        if error_rate > self.error_rate_threshold:
            issues.append(f"High error rate: {error_rate:.1%} > {self.error_rate_threshold:.1%}")
        if latency_trend > 0:
            issues.append(f"Latency increasing: +{latency_trend:.1f}ms")

        if issues:
            status = HealthStatus.DEGRADED if error_rate < 0.5 else HealthStatus.UNHEALTHY
        else:
            status = HealthStatus.HEALTHY

        return {
            "status": status.name,
            "avg_latency": round(avg_latency, 2),
            "error_rate": round(error_rate, 3),
            "latency_trend": round(latency_trend, 2),
            "issues": issues,
        }

    def detect_all(self, scheduler: ProbeScheduler) -> Dict[str, Dict[str, Any]]:
        return {
            probe_id: self.analyze(scheduler.get_results(probe_id))
            for probe_id in scheduler._probes
        }


class HealthMonitor:
    """Aggregate health status across all probes."""

    def __init__(self):
        self.scheduler = ProbeScheduler()
        self.degradation = DegradationDetector()
        self._components: Dict[str, str] = {}

    def add_probe(self, name: str, probe_type: ProbeType,
                  check_fn: Callable[[], Tuple[bool, float, str]],
                  interval: float = 60.0) -> HealthProbe:
        probe = HealthProbe(
            probe_id=str(uuid.uuid4())[:12],
            name=name,
            probe_type=probe_type,
            check_fn=check_fn,
            interval=interval,
        )
        self.scheduler.register(probe)
        return probe

    def check_all(self) -> Dict[str, ProbeResult]:
        return self.scheduler.run_all()

    def get_overall_status(self) -> HealthStatus:
        results = {pid: self.scheduler.get_latest(pid) for pid in self.scheduler._probes}
        statuses = [r.status for r in results.values() if r]
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        if any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        if all(s == HealthStatus.HEALTHY for s in statuses) and statuses:
            return HealthStatus.HEALTHY
        return HealthStatus.UNKNOWN

    def get_component_status(self, probe_id: str) -> Dict[str, Any]:
        latest = self.scheduler.get_latest(probe_id)
        results = self.scheduler.get_results(probe_id)
        analysis = self.degradation.analyze(results)
        return {
            "probe_id": probe_id,
            "latest": {
                "success": latest.success if latest else None,
                "latency_ms": latest.latency_ms if latest else None,
                "message": latest.message if latest else None,
                "status": latest.status.name if latest else "unknown",
            },
            "analysis": analysis,
        }

    def get_health_report(self) -> Dict[str, Any]:
        overall = self.get_overall_status()
        components = {}
        for pid in self.scheduler._probes:
            components[pid] = self.get_component_status(pid)
        return {
            "overall": overall.name,
            "timestamp": time.time(),
            "components": components,
            "degradation_analysis": self.degradation.detect_all(self.scheduler),
        }

    def export_report(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.get_health_report(), f, indent=2)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "probes": len(self.scheduler._probes),
            "overall_status": self.get_overall_status().name,
            "healthy": sum(1 for p in self.scheduler._probes if self.scheduler.get_latest(p) and self.scheduler.get_latest(p).status == HealthStatus.HEALTHY),
        }


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("HEALTH MONITOR DEMO")
    print("=" * 70)

    # 1. Setup probes
    print("\n[1] Setup Probes")
    monitor = HealthMonitor()
    monitor.add_probe("API Endpoint", ProbeType.HTTP,
                      lambda: (True, 45.0, "API responding"), interval=10.0)
    monitor.add_probe("Database", ProbeType.CUSTOM,
                      lambda: (True, 20.0, "DB connected"), interval=15.0)
    monitor.add_probe("Memory", ProbeType.MEMORY,
                      lambda: (True, 5.0, "Memory OK"), interval=30.0)
    monitor.add_probe("Flaky Service", ProbeType.HTTP,
                      lambda: (time.time() % 10 > 3, 200.0, "Intermittent"), interval=5.0)
    print(f"  Probes registered: {len(monitor.scheduler._probes)}")

    # 2. Run probes
    print("\n[2] Run Probes")
    results = monitor.check_all()
    for pid, result in results.items():
        print(f"  {result.probe_id}: {result.status.name} ({result.latency_ms:.1f}ms) - {result.message}")

    # 3. Simulate multiple runs
    print("\n[3] Simulate Multiple Runs")
    for i in range(5):
        monitor.scheduler.run_all()
    for pid in monitor.scheduler._probes:
        latest = monitor.scheduler.get_latest(pid)
        print(f"  {latest.probe_id}: success={latest.success}, consec_fail={latest.consecutive_failure}, status={latest.status.name}")

    # 4. Degradation detection
    print("\n[4] Degradation Detection")
    for pid in monitor.scheduler._probes:
        analysis = monitor.get_component_status(pid)["analysis"]
        print(f"  {pid}: {analysis['status']}, issues={analysis['issues']}")

    # 5. Overall status
    print(f"\n[5] Overall Status: {monitor.get_overall_status().name}")

    # 6. Health report
    print("\n[6] Health Report")
    report = monitor.get_health_report()
    print(f"  Overall: {report['overall']}")
    print(f"  Components: {len(report['components'])}")

    # 7. Export
    print("\n[7] Export Report")
    monitor.export_report("/tmp/health_report.json")
    print("  Exported to /tmp/health_report.json")

    # 8. Stats
    print(f"\n[8] Stats")
    print(f"  {monitor.get_stats()}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
