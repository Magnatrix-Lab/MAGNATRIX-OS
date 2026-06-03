"""
llm_metrics_exporter_native.py
MAGNATRIX-OS Metrics Exporter Engine
Native Python, stdlib only.
Provides metrics collection, aggregation, and Prometheus-style export with
counters, gauges, histograms, and summaries. Supports filtering, labeling, and export formats.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Callable


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricValue:
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {"value": self.value, "labels": self.labels, "timestamp": self.timestamp}


@dataclass
class MetricSeries:
    name: str
    metric_type: MetricType
    description: str
    values: List[MetricValue] = field(default_factory=list)
    unit: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "description": self.description,
            "unit": self.unit,
            "values": [v.to_dict() for v in self.values],
        }


@dataclass
class HistogramBucket:
    upper_bound: float
    count: int

    def to_dict(self) -> Dict[str, Any]:
        return {"upper_bound": self.upper_bound, "count": self.count}


@dataclass
class HistogramSnapshot:
    buckets: List[HistogramBucket]
    sum_value: float
    count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "buckets": [b.to_dict() for b in self.buckets],
            "sum": self.sum_value,
            "count": self.count,
        }


class MetricsExporterEngine:
    """
    Metrics collection and export engine with Prometheus-compatible output.
    """

    def __init__(self, namespace: str = "magnatrix") -> None:
        self.namespace = namespace
        self._series: Dict[str, MetricSeries] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._histogram_buckets: Dict[str, List[float]] = {}
        self._lock = False
        self._callbacks: Dict[str, Callable[[], float]] = {}

    def _key(self, name: str) -> str:
        return f"{self.namespace}_{name}"

    def register_counter(self, name: str, description: str, unit: str = "") -> None:
        key = self._key(name)
        self._series[key] = MetricSeries(name=key, metric_type=MetricType.COUNTER,
                                          description=description, unit=unit)

    def register_gauge(self, name: str, description: str, callback: Optional[Callable[[], float]] = None, unit: str = "") -> None:
        key = self._key(name)
        self._series[key] = MetricSeries(name=key, metric_type=MetricType.GAUGE,
                                          description=description, unit=unit)
        if callback:
            self._callbacks[key] = callback

    def register_histogram(self, name: str, description: str, buckets: List[float], unit: str = "") -> None:
        key = self._key(name)
        self._series[key] = MetricSeries(name=key, metric_type=MetricType.HISTOGRAM,
                                          description=description, unit=unit)
        self._histograms[key] = []
        self._histogram_buckets[key] = sorted(buckets)

    def register_summary(self, name: str, description: str, unit: str = "") -> None:
        key = self._key(name)
        self._series[key] = MetricSeries(name=key, metric_type=MetricType.SUMMARY,
                                          description=description, unit=unit)

    def increment(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        key = self._key(name)
        if key not in self._series:
            self.register_counter(name, f"Auto-registered {name}")
        self._series[key].values.append(MetricValue(value, labels or {}))

    def record(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        key = self._key(name)
        if key not in self._series:
            self.register_gauge(name, f"Auto-registered {name}")
        self._series[key].values.append(MetricValue(value, labels or {}))

    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        key = self._key(name)
        if key not in self._histograms:
            self.register_histogram(name, f"Auto-registered {name}",
                                     buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0])
        self._histograms[key].append(value)
        self._series[key].values.append(MetricValue(value, labels or {}))

    def observe_summary(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        key = self._key(name)
        if key not in self._series:
            self.register_summary(name, f"Auto-registered {name}")
        self._series[key].values.append(MetricValue(value, labels or {}))

    def _snapshot_histogram(self, key: str) -> HistogramSnapshot:
        buckets = self._histogram_buckets.get(key, [])
        values = self._histograms.get(key, [])
        bucket_counts = []
        cumulative = 0
        for b in sorted(buckets):
            count = sum(1 for v in values if v <= b)
            cumulative = count
            bucket_counts.append(HistogramBucket(upper_bound=b, count=cumulative))
        # +Inf bucket
        bucket_counts.append(HistogramBucket(upper_bound=float("inf"), count=len(values)))
        return HistogramSnapshot(buckets=bucket_counts, sum_value=sum(values), count=len(values))

    def get_series(self, name: str) -> Optional[MetricSeries]:
        return self._series.get(self._key(name))

    def get_all_series(self) -> List[MetricSeries]:
        return list(self._series.values())

    def clear(self, name: Optional[str] = None) -> None:
        if name:
            key = self._key(name)
            if key in self._series:
                self._series[key].values.clear()
            if key in self._histograms:
                self._histograms[key].clear()
        else:
            for s in self._series.values():
                s.values.clear()
            for h in self._histograms.values():
                h.clear()

    def to_prometheus(self, filter_prefix: Optional[str] = None) -> str:
        lines: List[str] = []
        for series in self._series.values():
            if filter_prefix and not series.name.startswith(filter_prefix):
                continue
            # Update gauge callbacks
            if series.metric_type == MetricType.GAUGE and series.name in self._callbacks:
                val = self._callbacks[series.name]()
                series.values.append(MetricValue(val))

            lines.append(f"# HELP {series.name} {series.description}")
            lines.append(f"# TYPE {series.name} {series.metric_type.value}")

            if series.metric_type == MetricType.HISTOGRAM and series.name in self._histograms:
                snap = self._snapshot_histogram(series.name)
                for b in snap.buckets:
                    labels_str = f'le="{b.upper_bound}"'
                    lines.append(f'{series.name}_bucket{{{labels_str}}} {b.count}')
                lines.append(f'{series.name}_sum {snap.sum_value}')
                lines.append(f'{series.name}_count {snap.count}')
            else:
                for mv in series.values[-100:]:  # Last 100 values
                    labels_str = ",".join(f'{k}="{v}"' for k, v in mv.labels.items())
                    if labels_str:
                        lines.append(f'{series.name}{{{labels_str}}} {mv.value}')
                    else:
                        lines.append(f'{series.name} {mv.value}')
            lines.append("")
        return "\n".join(lines)

    def to_json(self, filter_prefix: Optional[str] = None) -> str:
        data: Dict[str, Any] = {}
        for series in self._series.values():
            if filter_prefix and not series.name.startswith(filter_prefix):
                continue
            data[series.name] = series.to_dict()
            if series.metric_type == MetricType.HISTOGRAM and series.name in self._histograms:
                data[series.name]["snapshot"] = self._snapshot_histogram(series.name).to_dict()
        return json.dumps(data, indent=2, default=str)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.to_dict() for k, v in self._series.items()}

    def get_summary(self, name: str) -> Dict[str, Any]:
        key = self._key(name)
        series = self._series.get(key)
        if not series or not series.values:
            return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0}
        vals = [v.value for v in series.values]
        return {
            "count": len(vals),
            "sum": sum(vals),
            "avg": sum(vals) / len(vals),
            "min": min(vals),
            "max": max(vals),
        }


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Metrics Exporter Engine")
    print("=" * 60)

    engine = MetricsExporterEngine(namespace="magnatrix")

    # Register metrics
    engine.register_counter("requests_total", "Total requests processed", "count")
    engine.register_gauge("active_connections", "Currently active connections", unit="connections")
    engine.register_histogram("request_duration_seconds", "Request duration", buckets=[0.01, 0.05, 0.1, 0.5, 1.0], unit="seconds")
    engine.register_summary("response_size_bytes", "Response size in bytes", unit="bytes")

    # Record data
    for i in range(10):
        engine.increment("requests_total", 1, labels={"method": "POST", "endpoint": "/generate"})
        engine.record("active_connections", float(5 + i % 3))
        engine.observe_histogram("request_duration_seconds", 0.02 + (i * 0.05))
        engine.observe_summary("response_size_bytes", 1024 + (i * 256))

    print("\n--- Prometheus Format ---")
    prom = engine.to_prometheus()
    print(prom[:800] + "\n...")

    print("\n--- JSON Export ---")
    jsn = engine.to_json()
    print(jsn[:600] + "\n...")

    print("\n--- Summary Stats ---")
    for name in ["request_duration_seconds", "response_size_bytes"]:
        stats = engine.get_summary(name)
        print(f"  {name}: count={stats['count']} avg={stats['avg']:.2f} min={stats['min']:.2f} max={stats['max']:.2f}")

    print("\nMetrics Exporter test complete.")


if __name__ == "__main__":
    run()
