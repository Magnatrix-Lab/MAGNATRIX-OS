#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — Monitor Dashboard (Layer 0 Extension)
Metrics Collection, Health Checks, HTTP Status Dashboard
================================================================================
Zero-dependency monitoring: Prometheus-style counters/gauges/histograms,
layer health probes, and built-in HTTP server for live dashboard.
================================================================================
"""
from __future__ import annotations

import http.server
import json
import socketserver
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# =============================================================================
# Constants
# =============================================================================
DEFAULT_METRICS_PORT = 17779
DEFAULT_SCRAPE_INTERVAL = 15.0


# =============================================================================
# Metric Types
# =============================================================================
class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricSample:
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


# =============================================================================
# Counter
# =============================================================================
class Counter:
    def __init__(self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None) -> None:
        self.name = name
        self.description = description
        self._labels = labels or {}
        self._value = 0.0
        self._lock = threading.Lock()

    def inc(self, amount: float = 1.0) -> None:
        with self._lock:
            self._value += amount

    def get(self) -> float:
        with self._lock:
            return self._value

    def sample(self) -> MetricSample:
        return MetricSample(self.name, self.get(), dict(self._labels))

    def to_prometheus(self) -> str:
        lines = [f"# HELP {self.name} {self.description}", f"# TYPE {self.name} counter"]
        label_str = ",".join(f'{k}="{v}"' for k, v in self._labels.items())
        if label_str:
            lines.append(f'{self.name}{{{label_str}}} {self.get()}')
        else:
            lines.append(f'{self.name} {self.get()}')
        return "\n".join(lines)


# =============================================================================
# Gauge
# =============================================================================
class Gauge:
    def __init__(self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None) -> None:
        self.name = name
        self.description = description
        self._labels = labels or {}
        self._value = 0.0
        self._lock = threading.Lock()

    def set(self, value: float) -> None:
        with self._lock:
            self._value = value

    def inc(self, amount: float = 1.0) -> None:
        with self._lock:
            self._value += amount

    def dec(self, amount: float = 1.0) -> None:
        with self._lock:
            self._value -= amount

    def get(self) -> float:
        with self._lock:
            return self._value

    def sample(self) -> MetricSample:
        return MetricSample(self.name, self.get(), dict(self._labels))

    def to_prometheus(self) -> str:
        lines = [f"# HELP {self.name} {self.description}", f"# TYPE {self.name} gauge"]
        label_str = ",".join(f'{k}="{v}"' for k, v in self._labels.items())
        if label_str:
            lines.append(f'{self.name}{{{label_str}}} {self.get()}')
        else:
            lines.append(f'{self.name} {self.get()}')
        return "\n".join(lines)


# =============================================================================
# Histogram
# =============================================================================
class Histogram:
    def __init__(self, name: str, description: str = "", buckets: Optional[List[float]] = None) -> None:
        self.name = name
        self.description = description
        self.buckets = sorted(buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0])
        self._counts: Dict[float, int] = {b: 0 for b in self.buckets}
        self._sum = 0.0
        self._count = 0
        self._lock = threading.Lock()

    def observe(self, value: float) -> None:
        with self._lock:
            self._sum += value
            self._count += 1
            for b in self.buckets:
                if value <= b:
                    self._counts[b] += 1

    def get(self) -> Tuple[int, float, Dict[float, int]]:
        with self._lock:
            return self._count, self._sum, dict(self._counts)

    def to_prometheus(self) -> str:
        lines = [f"# HELP {self.name} {self.description}", f"# TYPE {self.name} histogram"]
        count, s, counts = self.get()
        for b in self.buckets:
            lines.append(f'{self.name}_bucket{{le="{b}"}} {counts.get(b, 0)}')
        lines.append(f'{self.name}_bucket{{le="+Inf"}} {count}')
        lines.append(f'{self.name}_sum {s}')
        lines.append(f'{self.name}_count {count}')
        return "\n".join(lines)


# =============================================================================
# Registry
# =============================================================================
class MetricsRegistry:
    """Central registry for all metrics."""

    def __init__(self) -> None:
        self._metrics: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def register(self, metric: Any) -> None:
        with self._lock:
            self._metrics[metric.name] = metric

    def get(self, name: str) -> Optional[Any]:
        with self._lock:
            return self._metrics.get(name)

    def counter(self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None) -> Counter:
        with self._lock:
            if name in self._metrics:
                return self._metrics[name]
            c = Counter(name, description, labels)
            self._metrics[name] = c
            return c

    def gauge(self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None) -> Gauge:
        with self._lock:
            if name in self._metrics:
                return self._metrics[name]
            g = Gauge(name, description, labels)
            self._metrics[name] = g
            return g

    def histogram(self, name: str, description: str = "", buckets: Optional[List[float]] = None) -> Histogram:
        with self._lock:
            if name in self._metrics:
                return self._metrics[name]
            h = Histogram(name, description, buckets)
            self._metrics[name] = h
            return h

    def collect(self) -> str:
        with self._lock:
            return "\n\n".join(m.to_prometheus() for m in self._metrics.values())

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {name: {"type": type(m).__name__.lower(), "value": getattr(m, "get", lambda: None)()} for name, m in self._metrics.items()}


# =============================================================================
# Health Probe
# =============================================================================
class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthReport:
    layer: str
    status: HealthStatus
    latency_ms: float
    message: str = ""
    checked_at: float = field(default_factory=time.time)


class HealthProbe(ABC):
    @abstractmethod
    def check(self) -> HealthReport: ...


class CallableProbe(HealthProbe):
    def __init__(self, layer: str, fn: Callable[[], Tuple[HealthStatus, str]], timeout: float = 5.0) -> None:
        self.layer = layer
        self.fn = fn
        self.timeout = timeout

    def check(self) -> HealthReport:
        t0 = time.perf_counter()
        try:
            status, msg = self.fn()
        except Exception as exc:
            status = HealthStatus.UNHEALTHY
            msg = str(exc)
        return HealthReport(
            layer=self.layer,
            status=status,
            latency_ms=(time.perf_counter() - t0) * 1000,
            message=msg,
        )


# =============================================================================
# Health Monitor
# =============================================================================
class HealthMonitor:
    """Periodic health checks across all layers."""

    def __init__(self, interval: float = DEFAULT_SCRAPE_INTERVAL) -> None:
        self.interval = interval
        self._probes: Dict[str, HealthProbe] = {}
        self._history: List[HealthReport] = []
        self._max_history = 1000
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def register(self, probe: HealthProbe) -> None:
        self._probes[probe.layer] = probe

    def check_all(self) -> List[HealthReport]:
        reports = []
        for probe in self._probes.values():
            r = probe.check()
            reports.append(r)
            with self._lock:
                self._history.append(r)
                if len(self._history) > self._max_history:
                    self._history = self._history[-self._max_history:]
        return reports

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while self._running:
            self.check_all()
            time.sleep(self.interval)

    def stop(self) -> None:
        self._running = False

    def get_history(self, layer: Optional[str] = None, limit: int = 100) -> List[HealthReport]:
        with self._lock:
            hist = list(self._history)
        if layer:
            hist = [h for h in hist if h.layer == layer]
        return hist[-limit:]

    def summary(self) -> Dict[str, Any]:
        latest: Dict[str, HealthReport] = {}
        with self._lock:
            for h in reversed(self._history):
                if h.layer not in latest:
                    latest[h.layer] = h
        return {
            "overall": HealthStatus.HEALTHY.value if all(r.status == HealthStatus.HEALTHY for r in latest.values()) else HealthStatus.DEGRADED.value,
            "layers": {layer: {"status": r.status.value, "latency_ms": r.latency_ms, "message": r.message, "checked_at": r.checked_at} for layer, r in latest.items()},
        }


# =============================================================================
# HTTP Dashboard
# =============================================================================
class DashboardHandler(http.server.BaseHTTPRequestHandler):
    registry: MetricsRegistry = MetricsRegistry()
    monitor: HealthMonitor = HealthMonitor()

    def log_message(self, format: str, *args: Any) -> None:
        pass  # Suppress default logging

    def do_GET(self) -> None:
        if self.path == "/metrics":
            self._respond(200, self.registry.collect(), "text/plain")
        elif self.path == "/health":
            self._respond_json(200, self.monitor.summary())
        elif self.path == "/api/v1/layers":
            self._respond_json(200, self.monitor.summary())
        elif self.path == "/api/v1/metrics":
            self._respond_json(200, self.registry.snapshot())
        elif self.path == "/":
            html = self._generate_dashboard()
            self._respond(200, html, "text/html")
        else:
            self._respond(404, "Not found", "text/plain")

    def _respond(self, code: int, body: str, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def _respond_json(self, code: int, data: Any) -> None:
        self._respond(code, json.dumps(data, indent=2, default=str), "application/json")

    def _generate_dashboard(self) -> str:
        health = self.monitor.summary()
        metrics = self.registry.snapshot()
        rows = ""
        for layer, info in health.get("layers", {}).items():
            color = "#2ecc71" if info["status"] == "healthy" else "#f39c12" if info["status"] == "degraded" else "#e74c3c"
            rows += f"""
            <tr>
              <td>{layer}</td>
              <td style="color:{color};font-weight:bold">{info["status"]}</td>
              <td>{info["latency_ms"]:.1f}ms</td>
              <td>{info["message"]}</td>
            </tr>"""
        metric_rows = ""
        for name, info in metrics.items():
            metric_rows += f"<tr><td>{name}</td><td>{info['type']}</td><td>{info['value']}</td></tr>"
        return f"""<!DOCTYPE html>
<html><head><title>MAGNATRIX-OS Dashboard</title>
<style>body{{font-family:sans-serif;background:#111;color:#eee;padding:20px}}
table{{border-collapse:collapse;width:100%;margin:10px 0}}
th,td{{padding:8px;text-align:left;border-bottom:1px solid #333}}
th{{background:#222;color:#0f0}}</style></head>
<body>
<h1>MAGNATRIX-OS Monitor</h1>
<h2>Overall: {health.get("overall", "unknown")}</h2>
<table>
<tr><th>Layer</th><th>Status</th><th>Latency</th><th>Message</th></tr>
{rows}
</table>
<h2>Metrics</h2>
<table>
<tr><th>Name</th><th>Type</th><th>Value</th></tr>
{metric_rows}
</table>
<p><a href="/metrics">Prometheus format</a> | <a href="/health">Health JSON</a></p>
</body></html>"""


class DashboardServer:
    """Built-in HTTP server for live monitoring."""

    def __init__(self, port: int = DEFAULT_METRICS_PORT) -> None:
        self.port = port
        self._server: Optional[socketserver.ThreadingTCPServer] = None
        self._thread: Optional[threading.Thread] = None
        self.registry = MetricsRegistry()
        self.monitor = HealthMonitor()
        DashboardHandler.registry = self.registry
        DashboardHandler.monitor = self.monitor

    def start(self) -> None:
        self._server = socketserver.ThreadingTCPServer(("0.0.0.0", self.port), DashboardHandler)
        self._server.allow_reuse_address = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self.monitor.start()

    def stop(self) -> None:
        self.monitor.stop()
        if self._server:
            self._server.shutdown()

    def __enter__(self) -> DashboardServer:
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()


# =============================================================================
# Monitor Kernel Bridge
# =============================================================================
class MonitorKernelBridge:
    def __init__(self, server: DashboardServer, event_bus: Any = None) -> None:
        self.server = server
        self.bus = event_bus
        self._event_counter = server.registry.counter("magnatrix_events_total", "Total events processed")
        self._layer_gauges: Dict[str, Gauge] = {}

    def record_event(self, event_type: str, layer: str) -> None:
        self._event_counter.inc()
        if layer not in self._layer_gauges:
            self._layer_gauges[layer] = self.server.registry.gauge(f"magnatrix_layer_active{{layer=\"{layer}\"}}", f"Activity for {layer}")
        self._layer_gauges[layer].inc()
        if self.bus:
            self.bus.publish("monitor.event", {"type": event_type, "layer": layer})

    def set_layer_health(self, layer: str, status: HealthStatus, latency_ms: float) -> None:
        # Create/update health gauge
        g = self.server.registry.gauge(f"magnatrix_layer_health{{layer=\"{layer}\"}}", f"Health for {layer}")
        g.set(1.0 if status == HealthStatus.HEALTHY else 0.5 if status == HealthStatus.DEGRADED else 0.0)


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Monitor Dashboard Demo")
    print("=" * 60)
    server = DashboardServer(port=17780)
    server.start()
    print("Dashboard running at http://127.0.0.1:17780")
    # Register health probes
    def kernel_ok() -> Tuple[HealthStatus, str]:
        return HealthStatus.HEALTHY, "OK"
    def storage_ok() -> Tuple[HealthStatus, str]:
        return HealthStatus.DEGRADED, "High latency"
    server.monitor.register(CallableProbe("kernel", kernel_ok))
    server.monitor.register(CallableProbe("storage", storage_ok))
    # Record some metrics
    c = server.registry.counter("requests_total", "Total requests")
    h = server.registry.histogram("request_duration_seconds", "Request duration")
    for i in range(10):
        c.inc()
        h.observe(0.01 * (i + 1))
    time.sleep(0.2)
    reports = server.monitor.check_all()
    for r in reports:
        print(f"  {r.layer}: {r.status.value} ({r.latency_ms:.1f}ms)")
    print(f"Prometheus:\n{server.registry.collect()[:500]}...")
    server.stop()
    print("Demo complete.")


if __name__ == "__main__":
    run_demo()
