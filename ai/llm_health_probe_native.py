"""
llm_health_probe_native.py
MAGNATRIX-OS Health Probe System
Native Python, stdlib only.
Provides deep and surface health checks for the MAGNATRIX-OS ecosystem,
including LLM connectivity, memory usage, disk space, and service dependencies.
"""

from __future__ import annotations

import json
import os
import socket
import threading
import time
import urllib.request
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class ProbeSeverity(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ProbeType(Enum):
    SURFACE = "surface"
    DEEP = "deep"


@dataclass
class ProbeResult:
    name: str
    probe_type: ProbeType
    severity: ProbeSeverity
    message: str
    response_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    checked_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "probe_type": self.probe_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "response_time_ms": round(self.response_time_ms, 2),
            "metadata": self.metadata,
            "checked_at": self.checked_at,
        }


@dataclass
class HealthReport:
    overall: ProbeSeverity
    probes: List[ProbeResult]
    checked_at: float = field(default_factory=time.time)
    uptime_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": self.overall.value,
            "probes": [p.to_dict() for p in self.probes],
            "checked_at": self.checked_at,
            "uptime_seconds": round(self.uptime_seconds, 2),
        }


class HealthProbeEngine:
    """
    Health probe engine with surface and deep checks.
    Supports custom probes, periodic scheduling, and alerting.
    """

    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self._probes: List[Dict[str, Any]] = []
        self._results: List[ProbeResult] = []
        self._timeout = timeout_seconds
        self._lock = threading.Lock()
        self._started_at = time.time()
        self._scheduler: Optional[threading.Thread] = None
        self._stop_scheduler = threading.Event()
        self._alert_handlers: List[Callable[[ProbeResult], None]] = []

    def register_surface_probe(
        self, name: str, check_fn: Callable[[], tuple[bool, str]],
        metadata_fn: Optional[Callable[[], Dict[str, Any]]] = None
    ) -> None:
        self._probes.append({
            "name": name, "type": ProbeType.SURFACE,
            "check_fn": check_fn, "metadata_fn": metadata_fn,
        })

    def register_deep_probe(
        self, name: str, check_fn: Callable[[], tuple[bool, str]],
        metadata_fn: Optional[Callable[[], Dict[str, Any]]] = None
    ) -> None:
        self._probes.append({
            "name": name, "type": ProbeType.DEEP,
            "check_fn": check_fn, "metadata_fn": metadata_fn,
        })

    def add_alert_handler(self, handler: Callable[[ProbeResult], None]) -> None:
        self._alert_handlers.append(handler)

    def _execute_probe(self, probe: Dict[str, Any]) -> ProbeResult:
        start = time.time()
        try:
            ok, message = probe["check_fn"]()
            severity = ProbeSeverity.HEALTHY if ok else ProbeSeverity.CRITICAL
        except Exception as e:
            ok = False
            severity = ProbeSeverity.UNKNOWN
            message = f"Exception: {e}"
        elapsed = (time.time() - start) * 1000.0
        metadata = {}
        if probe.get("metadata_fn"):
            try:
                metadata = probe["metadata_fn"]() or {}
            except Exception:
                pass
        return ProbeResult(
            name=probe["name"], probe_type=probe["type"],
            severity=severity, message=message,
            response_time_ms=elapsed, metadata=metadata
        )

    def run_all(self, probe_type: Optional[ProbeType] = None) -> HealthReport:
        with self._lock:
            self._results.clear()
            probes = self._probes
            if probe_type:
                probes = [p for p in probes if p["type"] == probe_type]

            for probe in probes:
                result = self._execute_probe(probe)
                self._results.append(result)
                if result.severity in (ProbeSeverity.CRITICAL, ProbeSeverity.UNKNOWN):
                    for handler in self._alert_handlers:
                        try:
                            handler(result)
                        except Exception:
                            pass

            overall = self._compute_overall()
            uptime = time.time() - self._started_at
            return HealthReport(
                overall=overall, probes=list(self._results),
                uptime_seconds=uptime
            )

    def _compute_overall(self) -> ProbeSeverity:
        severities = [r.severity for r in self._results]
        if ProbeSeverity.CRITICAL in severities:
            return ProbeSeverity.CRITICAL
        if ProbeSeverity.UNKNOWN in severities:
            return ProbeSeverity.UNKNOWN
        if ProbeSeverity.WARNING in severities:
            return ProbeSeverity.WARNING
        return ProbeSeverity.HEALTHY

    def get_last_results(self) -> List[ProbeResult]:
        with self._lock:
            return list(self._results)

    def get_probe_result(self, name: str) -> Optional[ProbeResult]:
        with self._lock:
            for r in self._results:
                if r.name == name:
                    return r
        return None

    def start_periodic(self, interval_seconds: float = 30.0) -> None:
        def loop() -> None:
            while not self._stop_scheduler.is_set():
                self.run_all()
                time.sleep(interval_seconds)

        self._stop_scheduler.clear()
        self._scheduler = threading.Thread(target=loop, daemon=True)
        self._scheduler.start()

    def stop_periodic(self) -> None:
        self._stop_scheduler.set()
        if self._scheduler:
            self._scheduler.join(timeout=2.0)

    def check_tcp(self, host: str, port: int, timeout: float = 2.0) -> tuple[bool, str]:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True, f"TCP {host}:{port} reachable"
        except Exception as e:
            return False, f"TCP {host}:{port} unreachable: {e}"

    def check_http(self, url: str, timeout: float = 3.0) -> tuple[bool, str]:
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return True, f"HTTP {resp.status} for {url}"
        except Exception as e:
            return False, f"HTTP check failed for {url}: {e}"

    def check_disk(self, path: str = "/", min_free_gb: float = 1.0) -> tuple[bool, str]:
        try:
            st = os.statvfs(path)
            free_gb = (st.f_bavail * st.f_frsize) / (1024 ** 3)
            if free_gb < min_free_gb:
                return False, f"Disk low: {free_gb:.2f} GB free (min {min_free_gb} GB)"
            return True, f"Disk OK: {free_gb:.2f} GB free"
        except Exception as e:
            return False, f"Disk check error: {e}"

    def check_memory(self, max_percent: float = 90.0) -> tuple[bool, str]:
        try:
            with open("/proc/meminfo", "r") as f:
                meminfo = f.read()
            total = 0
            available = 0
            for line in meminfo.splitlines():
                if line.startswith("MemTotal:"):
                    total = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    available = int(line.split()[1])
            if total > 0:
                used_pct = ((total - available) / total) * 100.0
                if used_pct > max_percent:
                    return False, f"Memory high: {used_pct:.1f}% used"
                return True, f"Memory OK: {used_pct:.1f}% used"
            return False, "Memory parse failed"
        except Exception as e:
            return False, f"Memory check error: {e}"

    def summary(self) -> str:
        report = self.run_all()
        lines = [
            f"Health: {report.overall.value}",
            f"Uptime: {report.uptime_seconds:.1f}s",
            f"Probes: {len(report.probes)}",
        ]
        for p in report.probes:
            icon = "✓" if p.severity == ProbeSeverity.HEALTHY else "✗"
            lines.append(f"  {icon} [{p.probe_type.value}] {p.name}: {p.severity.value} ({p.message})")
        return "\n".join(lines)


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Health Probe System")
    print("=" * 60)

    engine = HealthProbeEngine(timeout_seconds=5.0)

    # Surface probes
    engine.register_surface_probe(
        "disk_space",
        lambda: engine.check_disk("/", min_free_gb=0.5),
        lambda: {"path": "/", "threshold_gb": 0.5}
    )
    engine.register_surface_probe(
        "memory_usage",
        lambda: engine.check_memory(max_percent=95.0),
        lambda: {"max_percent": 95.0}
    )
    engine.register_surface_probe(
        "localhost_tcp",
        lambda: engine.check_tcp("127.0.0.1", 22, timeout=1.0),
    )

    # Deep probes
    engine.register_deep_probe(
        "github_connectivity",
        lambda: engine.check_http("https://github.com", timeout=5.0),
    )
    engine.register_deep_probe(
        "llm_api_simulation",
        lambda: (True, "LLM API simulated healthy"),
        lambda: {"model": "gpt-4o", "latency_ms": 120}
    )

    # Alert handler
    def on_alert(result: ProbeResult) -> None:
        print(f"[ALERT] {result.name}: {result.severity.value} - {result.message}")

    engine.add_alert_handler(on_alert)

    print("\n--- Running All Probes ---")
    report = engine.run_all()

    print(f"\nOverall: {report.overall.value}")
    print(f"Uptime: {report.uptime_seconds:.2f}s")
    for probe in report.probes:
        d = probe.to_dict()
        print(f"\n  [{d['probe_type']}] {d['name']}")
        print(f"    Severity: {d['severity']}")
        print(f"    Message: {d['message']}")
        print(f"    Response Time: {d['response_time_ms']} ms")
        print(f"    Metadata: {d['metadata']}")

    print("\n--- Summary ---")
    print(engine.summary())

    print("\n--- JSON Export ---")
    print(json.dumps(report.to_dict(), indent=2, default=str))

    print("\n--- Surface Only ---")
    surface_report = engine.run_all(ProbeType.SURFACE)
    print(f"  Surface probes: {len(surface_report.probes)} -> {surface_report.overall.value}")

    print("\nHealth Probe test complete.")


if __name__ == "__main__":
    run()
