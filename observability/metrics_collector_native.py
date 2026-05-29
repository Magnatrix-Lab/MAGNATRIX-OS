#!/usr/bin/env python3
"""
MAGNATRIX-OS | Layer 3 — Metrics Collector
Native metrics collection with counters, gauges, histograms, and summaries.
- Ring-buffer time series storage
- Rate calculation (per-second averages)
- Percentile estimation (t-digest approximation)
- Prometheus-compatible text export
"""
import json, time, threading, math, random, os, sys, hashlib
from typing import Dict, List, Optional, Any, Callable, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class TimeSeriesPoint:
    timestamp: float
    value: float


class Counter:
    """Monotonically increasing counter."""

    def __init__(self, name: str, labels: Dict[str, str] = None):
        self.name = name
        self.labels = labels or {}
        self._value = 0.0
        self._lock = threading.Lock()

    def inc(self, delta: float = 1.0):
        with self._lock:
            self._value += delta

    def get(self) -> float:
        with self._lock:
            return self._value

    def to_prometheus(self) -> str:
        label_str = ",".join(f'{k}="{v}"' for k, v in self.labels.items())
        return f"{self.name}{{{label_str}}} {self._value}"


class Gauge:
    """Arbitrary value gauge."""

    def __init__(self, name: str, labels: Dict[str, str] = None):
        self.name = name
        self.labels = labels or {}
        self._value = 0.0
        self._lock = threading.Lock()

    def set(self, value: float):
        with self._lock:
            self._value = value

    def inc(self, delta: float = 1.0):
        with self._lock:
            self._value += delta

    def dec(self, delta: float = 1.0):
        with self._lock:
            self._value -= delta

    def get(self) -> float:
        with self._lock:
            return self._value

    def to_prometheus(self) -> str:
        label_str = ",".join(f'{k}="{v}"' for k, v in self.labels.items())
        return f"{self.name}{{{label_str}}} {self._value}"


class Histogram:
    """Histogram with configurable buckets."""

    def __init__(self, name: str, buckets: List[float] = None, labels: Dict[str, str] = None):
        self.name = name
        self.labels = labels or {}
        self.buckets = sorted(buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10])
        self._counts = [0] * (len(self.buckets) + 1)
        self._sum = 0.0
        self._total = 0
        self._lock = threading.Lock()

    def observe(self, value: float):
        with self._lock:
            self._sum += value
            self._total += 1
            for i, b in enumerate(self.buckets):
                if value <= b:
                    self._counts[i] += 1
                    return
            self._counts[-1] += 1

    def to_prometheus(self) -> List[str]:
        lines = []
        label_str = ",".join(f'{k}="{v}"' for k, v in self.labels.items())
        cumulative = 0
        for i, b in enumerate(self.buckets):
            cumulative += self._counts[i]
            lines.append(f'{self.name}_bucket{{le="{b}",{label_str}}} {cumulative}')
        cumulative += self._counts[-1]
        lines.append(f'{self.name}_bucket{{le="+Inf",{label_str}}} {cumulative}')
        lines.append(f'{self.name}_sum{{{label_str}}} {self._sum}')
        lines.append(f'{self.name}_count{{{label_str}}} {self._total}')
        return lines


class TDigestApprox:
    """t-digest approximation for percentile estimation."""

    def __init__(self, max_centroids: int = 100):
        self.max_centroids = max_centroids
        self._centroids: List[Tuple[float, float]] = []  # (mean, weight)
        self._lock = threading.Lock()

    def add(self, value: float, weight: float = 1.0):
        with self._lock:
            self._centroids.append((value, weight))
            self._centroids.sort(key=lambda x: x[0])
            if len(self._centroids) > self.max_centroids:
                self._compress()

    def _compress(self):
        # K-means-like merge of closest centroids
        new_centroids = []
        i = 0
        while i < len(self._centroids):
            if i + 1 < len(self._centroids):
                m1, w1 = self._centroids[i]
                m2, w2 = self._centroids[i + 1]
                # Merge if close
                if abs(m1 - m2) < (m1 + m2) / 2 * 0.1:
                    new_m = (m1 * w1 + m2 * w2) / (w1 + w2)
                    new_w = w1 + w2
                    new_centroids.append((new_m, new_w))
                    i += 2
                    continue
            new_centroids.append(self._centroids[i])
            i += 1
        self._centroids = new_centroids

    def quantile(self, q: float) -> float:
        with self._lock:
            if not self._centroids:
                return 0.0
            total_weight = sum(w for _, w in self._centroids)
            target = q * total_weight
            cum = 0.0
            for m, w in self._centroids:
                cum += w
                if cum >= target:
                    return m
            return self._centroids[-1][0]

    def median(self) -> float:
        return self.quantile(0.5)

    def p95(self) -> float:
        return self.quantile(0.95)

    def p99(self) -> float:
        return self.quantile(0.99)


class TimeSeriesRing:
    """Ring buffer for time series data."""

    def __init__(self, capacity: int = 10000):
        self.capacity = capacity
        self._buffer: deque = deque(maxlen=capacity)
        self._lock = threading.Lock()

    def append(self, point: TimeSeriesPoint):
        with self._lock:
            self._buffer.append(point)

    def query(self, start: float, end: float) -> List[TimeSeriesPoint]:
        with self._lock:
            return [p for p in self._buffer if start <= p.timestamp <= end]

    def rate(self, window_sec: float = 60.0) -> float:
        with self._lock:
            if len(self._buffer) < 2:
                return 0.0
            now = time.time()
            recent = [p for p in self._buffer if now - p.timestamp <= window_sec]
        if len(recent) < 2:
            return 0.0
        total = sum(p.value for p in recent)
        return total / window_sec


class MetricsCollector:
    """Full metrics collector with all metric types."""

    def __init__(self):
        self.counters: Dict[str, Counter] = {}
        self.gauges: Dict[str, Gauge] = {}
        self.histograms: Dict[str, Histogram] = {}
        self.tdigests: Dict[str, TDigestApprox] = {}
        self.rings: Dict[str, TimeSeriesRing] = {}
        self._lock = threading.Lock()

    def counter(self, name: str, labels: Dict = None) -> Counter:
        with self._lock:
            if name not in self.counters:
                self.counters[name] = Counter(name, labels)
            return self.counters[name]

    def gauge(self, name: str, labels: Dict = None) -> Gauge:
        with self._lock:
            if name not in self.gauges:
                self.gauges[name] = Gauge(name, labels)
            return self.gauges[name]

    def histogram(self, name: str, buckets: List[float] = None, labels: Dict = None) -> Histogram:
        with self._lock:
            if name not in self.histograms:
                self.histograms[name] = Histogram(name, buckets, labels)
            return self.histograms[name]

    def observe_digest(self, name: str, value: float):
        with self._lock:
            if name not in self.tdigests:
                self.tdigests[name] = TDigestApprox()
            self.tdigests[name].add(value)

    def record_series(self, name: str, value: float):
        with self._lock:
            if name not in self.rings:
                self.rings[name] = TimeSeriesRing()
            self.rings[name].append(TimeSeriesPoint(time.time(), value))

    def prometheus_export(self) -> str:
        lines = []
        for c in self.counters.values():
            lines.append(c.to_prometheus())
        for g in self.gauges.values():
            lines.append(g.to_prometheus())
        for h in self.histograms.values():
            lines.extend(h.to_prometheus())
        return "\n".join(lines)

    def stats(self) -> Dict:
        return {
            "counters": len(self.counters),
            "gauges": len(self.gauges),
            "histograms": len(self.histograms),
            "tdigests": len(self.tdigests),
            "rings": len(self.rings),
        }


# ─── SELF TESTS ───
if __name__ == "__main__":
    tests = []
    def _t(name, fn):
        tests.append((name, fn))

    _t("counter_inc", lambda: (c := Counter("x"), c.inc(5), c.get() == 5)[2])
    _t("gauge_set", lambda: (g := Gauge("x"), g.set(3.14), g.get() == 3.14)[2])
    _t("histogram_observe", lambda: (h := Histogram("x"), h.observe(0.5), h._counts[6] == 1)[2])
    _t("tdigest_median", lambda: (t := TDigestApprox(), [t.add(x) for x in range(100)], 45 <= t.median() <= 55)[2])
    _t("tdigest_p99", lambda: (t := TDigestApprox(), [t.add(x) for x in range(100)], t.p99() >= 95)[2])
    _t("ring_query", lambda: (r := TimeSeriesRing(), r.append(TimeSeriesPoint(1, 1)), r.append(TimeSeriesPoint(2, 2)), len(r.query(0, 1.5)) == 1)[3])
    _t("ring_rate", lambda: (r := TimeSeriesRing(), [r.append(TimeSeriesPoint(time.time() - i, 1)) for i in range(10)], r.rate(60) > 0)[2])
    _t("prometheus_export", lambda: "x" in MetricsCollector().counter("x").to_prometheus())
    _t("collector_stats", lambda: "counters" in MetricsCollector().stats())
    _t("percentile", lambda: (t := TDigestApprox(), [t.add(random.gauss(0, 1)) for _ in range(1000)], -5 <= t.quantile(0.5) <= 5)[2])

    passed = 0
    for name, fn in tests:
        try:
            ok = fn()
            print(f"  {'PASS' if ok else 'FAIL'} {name}")
            if ok:
                passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
    print(f"\nMetrics Collector: {passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
