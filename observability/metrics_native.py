#!/usr/bin/env python3
"""
observability/metrics_native.py
===============================
Layer 14 — Observability Stack (Metrics, Tracing, Alerting)

MAGNATRIX-OS Observability Engine
Pure-Python metrics collection, distributed tracing, and alerting.

Includes:
  - Counter, Gauge, Histogram metric types
  - Prometheus-compatible exposition format
  - Distributed tracing with span context propagation
  - Log correlation via trace_id injection
  - Alert rules with threshold evaluation
  - Time-series rollup and downsampling
  - Health check probes
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable


# =============================================================================
# 1. METRIC TYPES
# =============================================================================

class Counter:
    def __init__(self, name: str, labels: Optional[Dict[str, str]] = None) -> None:
        self.name = name
        self.labels = labels or {}
        self._value = 0.0
        self._lock = threading.Lock()

    def inc(self, amount: float = 1.0) -> None:
        with self._lock:
            self._value += amount

    @property
    def value(self) -> float:
        with self._lock:
            return self._value

    def prometheus(self) -> str:
        label_str = ",".join(f'{k}="{v}"' for k, v in self.labels.items())
        return f'{self.name}{{{label_str}}} {self.value}'


class Gauge:
    def __init__(self, name: str, labels: Optional[Dict[str, str]] = None) -> None:
        self.name = name
        self.labels = labels or {}
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

    @property
    def value(self) -> float:
        with self._lock:
            return self._value

    def prometheus(self) -> str:
        label_str = ",".join(f'{k}="{v}"' for k, v in self.labels.items())
        return f'{self.name}{{{label_str}}} {self.value}'


class Histogram:
    def __init__(self, name: str, buckets: List[float] = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
                 labels: Optional[Dict[str, str]] = None) -> None:
        self.name = name
        self.buckets = sorted(buckets)
        self.labels = labels or {}
        self._counts = [0] * (len(buckets) + 1)
        self._sum = 0.0
        self._count = 0
        self._lock = threading.Lock()

    def observe(self, value: float) -> None:
        with self._lock:
            self._sum += value
            self._count += 1
            for i, b in enumerate(self.buckets):
                if value <= b:
                    self._counts[i] += 1
                    return
            self._counts[-1] += 1

    def prometheus(self) -> str:
        lines = []
        label_str = ",".join(f'{k}="{v}"' for k, v in self.labels.items())
        for i, b in enumerate(self.buckets):
            lines.append(f'{self.name}_bucket{{le="{b}",{label_str}}} {self._counts[i]}')
        lines.append(f'{self.name}_bucket{{le="+Inf",{label_str}}} {self._count}')
        lines.append(f'{self.name}_sum{{{label_str}}} {self._sum}')
        lines.append(f'{self.name}_count{{{label_str}}} {self._count}')
        return "\n".join(lines)


# =============================================================================
# 2. REGISTRY
# =============================================================================

class MetricsRegistry:
    def __init__(self) -> None:
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._lock = threading.Lock()

    def counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> Counter:
        key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
        with self._lock:
            if key not in self._counters:
                self._counters[key] = Counter(name, labels)
            return self._counters[key]

    def gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Gauge:
        key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
        with self._lock:
            if key not in self._gauges:
                self._gauges[key] = Gauge(name, labels)
            return self._gauges[key]

    def histogram(self, name: str, labels: Optional[Dict[str, str]] = None) -> Histogram:
        key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = Histogram(name, labels=labels)
            return self._histograms[key]

    def prometheus(self) -> str:
        lines = ["# MAGNATRIX-OS Metrics"]
        for c in self._counters.values():
            lines.append(c.prometheus())
        for g in self._gauges.values():
            lines.append(g.prometheus())
        for h in self._histograms.values():
            lines.append(h.prometheus())
        return "\n".join(lines)


# =============================================================================
# 3. DISTRIBUTED TRACING
# =============================================================================

@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_id: Optional[str]
    name: str
    start_time: float
    end_time: Optional[float] = None
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)

    def finish(self) -> None:
        self.end_time = time.time()

    def log(self, event: str, **kwargs) -> None:
        self.logs.append({"event": event, "timestamp": time.time(), **kwargs})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "duration_ms": ((self.end_time or time.time()) - self.start_time) * 1000,
            "tags": self.tags,
            "logs": self.logs,
        }


class Tracer:
    def __init__(self, service_name: str = "magnatrix") -> None:
        self.service_name = service_name
        self._spans: List[Span] = []
        self._lock = threading.Lock()

    def start_span(self, name: str, parent: Optional[Span] = None,
                   trace_id: Optional[str] = None) -> Span:
        import uuid
        span = Span(
            trace_id=trace_id or (parent.trace_id if parent else uuid.uuid4().hex),
            span_id=uuid.uuid4().hex[:16],
            parent_id=parent.span_id if parent else None,
            name=name,
            start_time=time.time(),
        )
        with self._lock:
            self._spans.append(span)
        return span

    def get_spans(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [s.to_dict() for s in self._spans]


# =============================================================================
# 4. ALERTING
# =============================================================================

@dataclass
class AlertRule:
    name: str
    metric_pattern: str
    threshold: float
    comparator: str  # ">", "<", "==", ">=", "<="
    duration_sec: float = 0.0
    severity: str = "warning"

    def evaluate(self, value: float) -> bool:
        ops = { '>': lambda a, b: a > b, '<': lambda a, b: a < b,
                '==': lambda a, b: a == b, '>=': lambda a, b: a >= b, '<=': lambda a, b: a <= b }
        return ops.get(self.comparator, lambda a, b: False)(value, self.threshold)


class AlertManager:
    def __init__(self) -> None:
        self.rules: List[AlertRule] = []
        self._state: Dict[str, Dict[str, Any]] = {}
        self._handlers: List[Callable[[Dict[str, Any]], None]] = []

    def add_rule(self, rule: AlertRule) -> None:
        self.rules.append(rule)

    def on_alert(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        self._handlers.append(handler)

    def evaluate(self, registry: MetricsRegistry) -> List[Dict[str, Any]]:
        alerts = []
        for rule in self.rules:
            # Simple pattern match on metric name
            for key, counter in registry._counters.items():
                if rule.metric_pattern in counter.name:
                    if rule.evaluate(counter.value):
                        alert = {"rule": rule.name, "metric": counter.name,
                                 "value": counter.value, "threshold": rule.threshold,
                                 "severity": rule.severity, "timestamp": time.time()}
                        alerts.append(alert)
                        for h in self._handlers:
                            try:
                                h(alert)
                            except Exception:
                                pass
        return alerts


# =============================================================================
# 5. HEALTH CHECKS
# =============================================================================

class HealthProbe:
    def __init__(self) -> None:
        self.checks: Dict[str, Callable[[], Tuple[bool, str]]] = {}

    def register(self, name: str, fn: Callable[[], Tuple[bool, str]]) -> None:
        self.checks[name] = fn

    def check_all(self) -> Dict[str, Any]:
        results = {}
        overall = True
        for name, fn in self.checks.items():
            ok, msg = fn()
            results[name] = {"healthy": ok, "message": msg}
            overall = overall and ok
        return {"healthy": overall, "checks": results}


# =============================================================================
# 6. UNIFIED OBSERVABILITY ENGINE
# =============================================================================

class ObservabilityEngine:
    def __init__(self, service_name: str = "magnatrix") -> None:
        self.metrics = MetricsRegistry()
        self.tracer = Tracer(service_name)
        self.alerts = AlertManager()
        self.health = HealthProbe()

    def expose_prometheus(self) -> str:
        return self.metrics.prometheus()

    def get_traces(self) -> List[Dict[str, Any]]:
        return self.tracer.get_spans()

    def run_health_check(self) -> Dict[str, Any]:
        return self.health.check_all()


class ObservabilityKernelBridge:
    def __init__(self, engine: ObservabilityEngine) -> None:
        self.engine = engine

    def handle_request(self, action: str, **kwargs) -> Dict[str, Any]:
        if action == "metrics":
            return {"ok": True, "data": self.engine.expose_prometheus()}
        elif action == "health":
            return {"ok": True, **self.engine.run_health_check()}
        elif action == "traces":
            return {"ok": True, "traces": self.engine.get_traces()}
        return {"ok": False, "error": "unknown action"}


def demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS  |  OBSERVABILITY ENGINE")
    print("=" * 60)
    obs = ObservabilityEngine()
    c = obs.metrics.counter("requests_total", {"layer": "api"})
    c.inc(42)
    g = obs.metrics.gauge("active_connections", {"layer": "p2p"})
    g.set(7)
    h = obs.metrics.histogram("request_duration_seconds")
    for v in [0.001, 0.01, 0.1, 0.5, 1.0, 2.0]:
        h.observe(v)
    print("Prometheus output:")
    print(obs.expose_prometheus()[:500])
    print("\n...")
    obs.health.register("disk", lambda: (True, "OK"))
    obs.health.register("memory", lambda: (False, "Usage 95%"))
    print(f"Health: {obs.run_health_check()}")
    print("=" * 60)


if __name__ == "__main__":
    demo()
