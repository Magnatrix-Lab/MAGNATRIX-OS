"""Monitoring & Observability — Metrics, tracing, health checks, dan alerting.

Modul ini menyediakan:
- MetricsCollector untuk counter, gauge, histogram metrics
- Tracer untuk distributed tracing spans
- HealthChecker untuk system health checks
- AlertManager dengan threshold-based alerting
- Dashboard exporter untuk metrics aggregation
"""

from __future__ import annotations

import json
import time
import uuid
import statistics
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class MetricType(Enum):
    COUNTER = auto()
    GAUGE = auto()
    HISTOGRAM = auto()
    TIMER = auto()


class AlertSeverity(Enum):
    INFO = auto()
    WARNING = auto()
    CRITICAL = auto()


@dataclass
class Metric:
    """Single metric point."""
    name: str
    metric_type: MetricType
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Span:
    """Tracing span."""
    span_id: str
    trace_id: str
    name: str
    start_time: float
    end_time: float = 0.0
    parent_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)

    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000 if self.end_time > 0 else 0.0


@dataclass
class HealthCheck:
    """Health check definition."""
    check_id: str
    name: str
    check_fn: Callable[[], Tuple[bool, str]]
    interval: float = 30.0
    last_run: float = 0.0
    last_status: bool = True
    last_message: str = ""


@dataclass
class Alert:
    """Alert instance."""
    alert_id: str
    name: str
    severity: AlertSeverity
    message: str
    metric_name: str
    threshold: float
    current_value: float
    timestamp: float
    resolved: bool = False
    resolved_at: Optional[float] = None


class MetricsCollector:
    """Collect dan aggregate metrics."""

    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self._metrics: Dict[str, List[Metric]] = {}
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}

    def record(self, metric: Metric) -> None:
        self._metrics.setdefault(metric.name, [])
        self._metrics[metric.name].append(metric)
        if len(self._metrics[metric.name]) > self.max_history:
            self._metrics[metric.name] = self._metrics[metric.name][-self.max_history:]
        if metric.metric_type == MetricType.COUNTER:
            self._counters[metric.name] = self._counters.get(metric.name, 0) + metric.value
        elif metric.metric_type == MetricType.GAUGE:
            self._gauges[metric.name] = metric.value

    def increment(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        self.record(Metric(name, MetricType.COUNTER, value, time.time(), labels or {}))

    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        self.record(Metric(name, MetricType.GAUGE, value, time.time(), labels or {}))

    def timer(self, name: str, duration_ms: float, labels: Optional[Dict[str, str]] = None) -> None:
        self.record(Metric(name, MetricType.TIMER, duration_ms, time.time(), labels or {}))

    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        self.record(Metric(name, MetricType.HISTOGRAM, value, time.time(), labels or {}))

    def get_counter(self, name: str) -> float:
        return self._counters.get(name, 0.0)

    def get_gauge(self, name: str) -> float:
        return self._gauges.get(name, 0.0)

    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        values = [m.value for m in self._metrics.get(name, [])]
        if not values:
            return {}
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": round(statistics.mean(values), 3),
            "median": round(statistics.median(values), 3),
            "p95": round(self._percentile(values, 0.95), 3) if len(values) >= 20 else round(max(values), 3),
            "p99": round(self._percentile(values, 0.99), 3) if len(values) >= 100 else round(max(values), 3)
        }

    def _percentile(self, values: List[float], p: float) -> float:
        sorted_vals = sorted(values)
        idx = int(p * len(sorted_vals))
        return sorted_vals[min(idx, len(sorted_vals) - 1)]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "metric_names": len(self._metrics),
            "total_samples": sum(len(v) for v in self._metrics.values()),
            "counters": dict(self._counters),
            "gauges": dict(self._gauges)
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "counters": self._counters,
                "gauges": self._gauges,
                "histograms": {k: self.get_histogram_stats(k) for k in self._metrics if any(m.metric_type == MetricType.HISTOGRAM for m in self._metrics[k])}
            }, f, indent=2)


class Tracer:
    """Distributed tracing untuk request flows."""

    def __init__(self):
        self._spans: Dict[str, List[Span]] = {}  # trace_id -> spans
        self._active_spans: Dict[str, Span] = {}  # span_id -> span

    def start_span(self, trace_id: str, name: str, parent_id: Optional[str] = None, tags: Optional[Dict[str, str]] = None) -> Span:
        span = Span(
            span_id=str(uuid.uuid4())[:12],
            trace_id=trace_id,
            name=name,
            start_time=time.time(),
            parent_id=parent_id,
            tags=tags or {}
        )
        self._spans.setdefault(trace_id, []).append(span)
        self._active_spans[span.span_id] = span
        return span

    def finish_span(self, span_id: str) -> Optional[Span]:
        span = self._active_spans.pop(span_id, None)
        if span:
            span.end_time = time.time()
        return span

    def log(self, span_id: str, message: str, fields: Optional[Dict[str, Any]] = None) -> None:
        span = self._active_spans.get(span_id)
        if span:
            span.logs.append({"time": time.time(), "message": message, "fields": fields or {}})

    def get_trace(self, trace_id: str) -> List[Span]:
        return self._spans.get(trace_id, [])

    def get_trace_stats(self, trace_id: str) -> Dict[str, Any]:
        spans = self._spans.get(trace_id, [])
        if not spans:
            return {}
        durations = [s.duration_ms() for s in spans if s.end_time > 0]
        return {
            "trace_id": trace_id,
            "span_count": len(spans),
            "total_duration_ms": round(sum(durations), 2),
            "avg_duration_ms": round(statistics.mean(durations), 2) if durations else 0,
            "root_span": spans[0].name if spans else None
        }

    def export_trace(self, trace_id: str, path: str) -> None:
        spans = self._spans.get(trace_id, [])
        with open(path, "w", encoding="utf-8") as f:
            json.dump([{
                "span_id": s.span_id,
                "name": s.name,
                "start": s.start_time,
                "end": s.end_time,
                "duration_ms": round(s.duration_ms(), 2),
                "parent_id": s.parent_id,
                "tags": s.tags
            } for s in spans], f, indent=2)


class HealthMonitor:
    """Monitor system health dengan periodic checks."""

    def __init__(self):
        self._checks: Dict[str, HealthCheck] = {}
        self._results: Dict[str, Tuple[bool, str]] = {}

    def add_check(self, check: HealthCheck) -> None:
        self._checks[check.check_id] = check

    def run_check(self, check_id: str) -> Tuple[bool, str]:
        check = self._checks.get(check_id)
        if not check:
            return False, "Check not found"
        try:
            status, message = check.check_fn()
            check.last_status = status
            check.last_message = message
            check.last_run = time.time()
            self._results[check_id] = (status, message)
            return status, message
        except Exception as e:
            check.last_status = False
            check.last_message = str(e)
            check.last_run = time.time()
            self._results[check_id] = (False, str(e))
            return False, str(e)

    def run_all(self) -> Dict[str, Tuple[bool, str]]:
        return {cid: self.run_check(cid) for cid in self._checks}

    def get_status(self) -> Dict[str, Any]:
        return {
            "overall": "healthy" if all(r[0] for r in self._results.values()) else "unhealthy",
            "checks": {
                cid: {"status": c.last_status, "message": c.last_message, "last_run": c.last_run}
                for cid, c in self._checks.items()
            }
        }

    def is_healthy(self) -> bool:
        return all(r[0] for r in self._results.values()) if self._results else True


class AlertManager:
    """Threshold-based alerting system."""

    def __init__(self):
        self._rules: Dict[str, Dict[str, Any]] = {}
        self._alerts: List[Alert] = []
        self._handlers: List[Callable[[Alert], None]] = []

    def add_rule(self, name: str, metric_name: str, threshold: float, comparison: str = ">", severity: AlertSeverity = AlertSeverity.WARNING, cooldown: float = 60.0) -> None:
        self._rules[name] = {
            "metric_name": metric_name,
            "threshold": threshold,
            "comparison": comparison,
            "severity": severity,
            "cooldown": cooldown,
            "last_triggered": 0.0
        }

    def evaluate(self, metrics: MetricsCollector) -> List[Alert]:
        triggered = []
        for name, rule in self._rules.items():
            if time.time() - rule["last_triggered"] < rule["cooldown"]:
                continue
            val = metrics.get_gauge(rule["metric_name"])
            if val == 0:
                val = metrics.get_counter(rule["metric_name"])
            comp = rule["comparison"]
            threshold = rule["threshold"]
            triggered_now = False
            if comp == ">" and val > threshold:
                triggered_now = True
            elif comp == "<" and val < threshold:
                triggered_now = True
            elif comp == ">=" and val >= threshold:
                triggered_now = True
            elif comp == "<=" and val <= threshold:
                triggered_now = True
            elif comp == "==" and val == threshold:
                triggered_now = True
            if triggered_now:
                rule["last_triggered"] = time.time()
                alert = Alert(
                    alert_id=str(uuid.uuid4())[:12],
                    name=name,
                    severity=rule["severity"],
                    message=f"{rule['metric_name']} {comp} {threshold} (current: {val})",
                    metric_name=rule["metric_name"],
                    threshold=threshold,
                    current_value=val,
                    timestamp=time.time()
                )
                self._alerts.append(alert)
                triggered.append(alert)
                for handler in self._handlers:
                    try:
                        handler(alert)
                    except Exception:
                        pass
        return triggered

    def resolve(self, alert_id: str) -> bool:
        for alert in self._alerts:
            if alert.alert_id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = time.time()
                return True
        return False

    def get_active_alerts(self) -> List[Alert]:
        return [a for a in self._alerts if not a.resolved]

    def get_alert_history(self, limit: int = 50) -> List[Alert]:
        return self._alerts[-limit:]

    def on_alert(self, handler: Callable[[Alert], None]) -> None:
        self._handlers.append(handler)

    def get_stats(self) -> Dict[str, Any]:
        active = self.get_active_alerts()
        return {
            "total_rules": len(self._rules),
            "total_alerts": len(self._alerts),
            "active_alerts": len(active),
            "by_severity": {
                "CRITICAL": sum(1 for a in active if a.severity == AlertSeverity.CRITICAL),
                "WARNING": sum(1 for a in active if a.severity == AlertSeverity.WARNING),
                "INFO": sum(1 for a in active if a.severity == AlertSeverity.INFO)
            }
        }


class DashboardExporter:
    """Export aggregated metrics untuk dashboard consumption."""

    def __init__(self, metrics: MetricsCollector, health: HealthMonitor, alerts: AlertManager):
        self.metrics = metrics
        self.health = health
        self.alerts = alerts

    def snapshot(self) -> Dict[str, Any]:
        return {
            "timestamp": time.time(),
            "metrics": self.metrics.get_stats(),
            "health": self.health.get_status(),
            "alerts": self.alerts.get_stats(),
            "histograms": {k: self.metrics.get_histogram_stats(k) for k in self.metrics._metrics}
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.snapshot(), f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("MONITORING & OBSERVABILITY DEMO")
    print("=" * 70)

    # 1. Metrics
    print("\n[1] Metrics Collection")
    metrics = MetricsCollector()
    for i in range(100):
        metrics.increment("requests_total", 1.0, {"endpoint": "/query", "method": "POST"})
        metrics.timer("request_duration_ms", 50 + (i % 50), {"endpoint": "/query"})
        metrics.gauge("active_connections", 10 + (i % 20))
        metrics.histogram("response_size_bytes", 1000 + (i * 100) % 5000)
    print(f"  Counters: {metrics.get_counter('requests_total')}")
    print(f"  Gauges: {metrics.get_gauge('active_connections')}")
    print(f"  Timer stats: {metrics.get_histogram_stats('request_duration_ms')}")
    print(f"  Size stats: {metrics.get_histogram_stats('response_size_bytes')}")

    # 2. Tracing
    print("\n[2] Distributed Tracing")
    tracer = Tracer()
    trace_id = "trace-123"
    root = tracer.start_span(trace_id, "process_request")
    child1 = tracer.start_span(trace_id, "embed_query", parent_id=root.span_id)
    time.sleep(0.01)
    tracer.log(child1.span_id, "embedding computed", {"dim": 768})
    tracer.finish_span(child1.span_id)
    child2 = tracer.start_span(trace_id, "search_index", parent_id=root.span_id)
    time.sleep(0.01)
    tracer.finish_span(child2.span_id)
    tracer.finish_span(root.span_id)
    print(f"  Trace stats: {tracer.get_trace_stats(trace_id)}")
    print(f"  Spans: {len(tracer.get_trace(trace_id))}")

    # 3. Health checks
    print("\n[3] Health Checks")
    health = HealthMonitor()
    health.add_check(HealthCheck("db", "Database", lambda: (True, "Connected"), interval=30))
    health.add_check(HealthCheck("llm", "LLM Service", lambda: (True, "Responding"), interval=30))
    health.add_check(HealthCheck("disk", "Disk Space", lambda: (False, "85% full"), interval=30))
    health.run_all()
    print(f"  Overall: {health.get_status()['overall']}")
    print(f"  Healthy: {health.is_healthy()}")

    # 4. Alerting
    print("\n[4] Alerting")
    alerts = AlertManager()
    alerts.on_alert(lambda a: print(f"    ALERT: {a.name} [{a.severity.name}] - {a.message}"))
    alerts.add_rule("high_latency", "request_duration_ms", 80, ">", AlertSeverity.WARNING, cooldown=0.1)
    alerts.add_rule("too_many_requests", "requests_total", 50, ">", AlertSeverity.INFO, cooldown=0.1)
    alerts.evaluate(metrics)
    print(f"  Active alerts: {len(alerts.get_active_alerts())}")
    print(f"  Alert stats: {alerts.get_stats()}")

    # 5. Dashboard
    print("\n[5] Dashboard Snapshot")
    dashboard = DashboardExporter(metrics, health, alerts)
    snap = dashboard.snapshot()
    print(f"  Snapshot keys: {list(snap.keys())}")
    dashboard.export("/tmp/dashboard.json")
    print(f"  Exported to /tmp/dashboard.json")

    # 6. Metrics export
    print("\n[6] Metrics Export")
    metrics.export("/tmp/metrics.json")
    print(f"  Exported metrics to /tmp/metrics.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
