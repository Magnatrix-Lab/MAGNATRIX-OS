#!/usr/bin/env python3
"""
Analytics Engine for MAGNATRIX-OS
Time-series data collection, real-time streaming metrics, aggregation pipelines,
anomaly detection with threshold alerts. Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import json
import math
import statistics
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


@dataclass
class TimeSeriesPoint:
    """A single point in a time series."""
    timestamp: float
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSeries:
    """A named time series of metrics."""
    name: str
    unit: str = ""
    retention_seconds: int = 86400
    data: deque = field(default_factory=lambda: deque(maxlen=10000))


@dataclass
class AlertRule:
    """A rule for triggering alerts."""
    id: str
    metric_name: str
    condition: str  # >, <, ==, >=, <=
    threshold: float
    duration: int  # seconds the condition must hold
    severity: str = "warning"  # info, warning, critical
    enabled: bool = True
    last_triggered: float = 0.0


@dataclass
class AlertEvent:
    """An alert that has been triggered."""
    rule_id: str
    metric_name: str
    value: float
    threshold: float
    severity: str
    timestamp: float
    acknowledged: bool = False


class TimeSeriesStore:
    """Store and query time-series data."""

    def __init__(self) -> None:
        self._series: Dict[str, MetricSeries] = {}
        self._lock = threading.RLock()

    def add_point(self, name: str, value: float, tags: Optional[Dict[str, str]] = None, timestamp: Optional[float] = None) -> None:
        with self._lock:
            if name not in self._series:
                self._series[name] = MetricSeries(name=name)
            ts = timestamp or time.time()
            self._series[name].data.append(TimeSeriesPoint(ts, value, tags or {}))

    def get_series(self, name: str, start: Optional[float] = None, end: Optional[float] = None) -> List[TimeSeriesPoint]:
        with self._lock:
            series = self._series.get(name)
            if not series:
                return []
            points = list(series.data)
            if start:
                points = [p for p in points if p.timestamp >= start]
            if end:
                points = [p for p in points if p.timestamp <= end]
            return points

    def list_series(self) -> List[str]:
        with self._lock:
            return sorted(self._series.keys())

    def stats(self, name: str) -> Dict[str, Any]:
        points = self.get_series(name)
        if not points:
            return {}
        values = [p.value for p in points]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0,
        }


class AggregationPipeline:
    """Pipeline for aggregating time-series data."""

    def __init__(self, store: TimeSeriesStore) -> None:
        self.store = store

    def aggregate(self, name: str, window_seconds: int, func: str = "mean") -> List[Dict[str, Any]]:
        """Aggregate data into time windows."""
        points = self.store.get_series(name)
        if not points:
            return []

        # Sort by time
        points.sort(key=lambda p: p.timestamp)

        # Group into windows
        windows: Dict[int, List[float]] = {}
        for p in points:
            window_key = int(p.timestamp // window_seconds) * window_seconds
            windows.setdefault(window_key, []).append(p.value)

        results = []
        for ts, values in sorted(windows.items()):
            if func == "sum":
                agg = sum(values)
            elif func == "count":
                agg = len(values)
            elif func == "min":
                agg = min(values)
            elif func == "max":
                agg = max(values)
            elif func == "mean":
                agg = statistics.mean(values)
            elif func == "median":
                agg = statistics.median(values)
            else:
                agg = statistics.mean(values)

            results.append({
                "timestamp": ts,
                "window_start": ts,
                "window_end": ts + window_seconds,
                "value": agg,
                "count": len(values),
            })

        return results

    def percentile(self, name: str, p: float) -> Optional[float]:
        points = self.store.get_series(name)
        if not points:
            return None
        values = sorted([p.value for p in points])
        k = (len(values) - 1) * p / 100
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return values[int(k)]
        return values[f] * (c - k) + values[c] * (k - f)

    def rate(self, name: str) -> Optional[float]:
        """Calculate rate of change per second."""
        points = self.store.get_series(name)
        if len(points) < 2:
            return None
        first, last = points[0], points[-1]
        dt = last.timestamp - first.timestamp
        if dt == 0:
            return 0
        return (last.value - first.value) / dt


class AnomalyDetector:
    """Detect anomalies in time-series data."""

    def __init__(self, store: TimeSeriesStore) -> None:
        self.store = store
        self._baselines: Dict[str, Dict[str, float]] = {}

    def learn_baseline(self, name: str, window: int = 3600) -> None:
        """Learn baseline statistics for a metric."""
        now = time.time()
        points = self.store.get_series(name, start=now - window)
        if len(points) < 10:
            return
        values = [p.value for p in points]
        self._baselines[name] = {
            "mean": statistics.mean(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0,
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "learned_at": now,
        }

    def detect(self, name: str, method: str = "zscore", threshold: float = 3.0) -> List[Dict[str, Any]]:
        """Detect anomalies in recent data."""
        if name not in self._baselines:
            self.learn_baseline(name)
        baseline = self._baselines.get(name)
        if not baseline:
            return []

        points = self.store.get_series(name, start=time.time() - 300)  # Last 5 min
        anomalies = []

        for p in points:
            if method == "zscore":
                zscore = abs(p.value - baseline["mean"]) / (baseline["stdev"] or 1)
                if zscore > threshold:
                    anomalies.append({
                        "timestamp": p.timestamp,
                        "value": p.value,
                        "zscore": zscore,
                        "expected": baseline["mean"],
                    })
            elif method == "iqr":
                q1 = baseline["median"] - 0.5 * baseline["stdev"]
                q3 = baseline["median"] + 0.5 * baseline["stdev"]
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                if p.value < lower or p.value > upper:
                    anomalies.append({
                        "timestamp": p.timestamp,
                        "value": p.value,
                        "expected_range": [lower, upper],
                    })
            elif method == "threshold":
                if p.value > threshold or p.value < -threshold:
                    anomalies.append({
                        "timestamp": p.timestamp,
                        "value": p.value,
                        "threshold": threshold,
                    })

        return anomalies


class AlertEngine:
    """Evaluate alert rules and trigger notifications."""

    def __init__(self, store: TimeSeriesStore) -> None:
        self.store = store
        self._rules: Dict[str, AlertRule] = {}
        self._events: deque = deque(maxlen=1000)
        self._running = False
        self._lock = threading.Lock()
        self._on_alert: Optional[Callable[[AlertEvent], None]] = None

    def add_rule(self, rule: AlertRule) -> None:
        with self._lock:
            self._rules[rule.id] = rule

    def remove_rule(self, rule_id: str) -> bool:
        with self._lock:
            return self._rules.pop(rule_id, None) is not None

    def check_all(self) -> List[AlertEvent]:
        """Evaluate all rules and trigger alerts."""
        triggered = []
        with self._lock:
            for rule in self._rules.values():
                if not rule.enabled:
                    continue
                points = self.store.get_series(rule.metric_name, start=time.time() - rule.duration)
                if not points:
                    continue
                values = [p.value for p in points]
                if not values:
                    continue

                # Check if condition holds for all points in window
                condition_met = all(self._check_condition(v, rule.condition, rule.threshold) for v in values)

                if condition_met:
                    event = AlertEvent(
                        rule_id=rule.id,
                        metric_name=rule.metric_name,
                        value=values[-1],
                        threshold=rule.threshold,
                        severity=rule.severity,
                        timestamp=time.time(),
                    )
                    self._events.append(event)
                    triggered.append(event)
                    rule.last_triggered = time.time()
                    if self._on_alert:
                        try:
                            self._on_alert(event)
                        except Exception:
                            pass
        return triggered

    def _check_condition(self, value: float, condition: str, threshold: float) -> bool:
        ops = {
            ">": lambda a, b: a > b,
            "<": lambda a, b: a < b,
            ">=": lambda a, b: a >= b,
            "<=": lambda a, b: a <= b,
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
        }
        return ops.get(condition, lambda a, b: False)(value, threshold)

    def get_events(self, limit: int = 50) -> List[AlertEvent]:
        return list(self._events)[-limit:]

    def get_active(self) -> List[AlertEvent]:
        return [e for e in self._events if not e.acknowledged]

    def acknowledge(self, rule_id: str) -> None:
        for e in self._events:
            if e.rule_id == rule_id:
                e.acknowledged = True

    def on_alert(self, callback: Callable[[AlertEvent], None]) -> None:
        self._on_alert = callback

    def start(self, check_interval: int = 10) -> None:
        self._running = True
        def loop():
            while self._running:
                self.check_all()
                time.sleep(check_interval)
        threading.Thread(target=loop, daemon=True, name="AlertEngine").start()

    def stop(self) -> None:
        self._running = False

    def list_rules(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": r.id, "metric": r.metric_name, "condition": r.condition,
                "threshold": r.threshold, "severity": r.severity, "enabled": r.enabled,
                "last_triggered": r.last_triggered,
            }
            for r in self._rules.values()
        ]


class AnalyticsEngine:
    """Main analytics engine combining all components."""

    def __init__(self, repo_root: str = "") -> None:
        self.root = Path(repo_root).resolve() if repo_root else Path.cwd()
        self.store = TimeSeriesStore()
        self.pipeline = AggregationPipeline(self.store)
        self.detector = AnomalyDetector(self.store)
        self.alerts = AlertEngine(self.store)
        self._collectors: List[threading.Thread] = []

    def record(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        self.store.add_point(name, value, tags)

    def query(self, name: str, start: Optional[float] = None, end: Optional[float] = None) -> List[TimeSeriesPoint]:
        return self.store.get_series(name, start, end)

    def aggregate(self, name: str, window: int = 60, func: str = "mean") -> List[Dict[str, Any]]:
        return self.pipeline.aggregate(name, window, func)

    def add_alert(self, metric_name: str, condition: str, threshold: float, duration: int = 60, severity: str = "warning") -> str:
        rule = AlertRule(
            id=f"alert_{int(time.time() * 1000)}",
            metric_name=metric_name,
            condition=condition,
            threshold=threshold,
            duration=duration,
            severity=severity,
        )
        self.alerts.add_rule(rule)
        return rule.id

    def start_collection(self, collectors: List[Tuple[str, Callable[[], float], int]]) -> None:
        """Start background metric collectors."""
        for name, fn, interval in collectors:
            def make_collector(n, f, i):
                def loop():
                    while True:
                        try:
                            self.record(n, f())
                        except Exception:
                            pass
                        time.sleep(i)
                return loop
            t = threading.Thread(target=make_collector(name, fn, interval), daemon=True, name=f"Collector-{name}")
            t.start()
            self._collectors.append(t)

    def start_alerts(self, interval: int = 10) -> None:
        self.alerts.start(interval)

    def stats(self) -> Dict[str, Any]:
        return {
            "series": self.store.list_series(),
            "series_count": len(self.store.list_series()),
            "alert_rules": len(self.alerts._rules),
            "alert_events": len(self.alerts._events),
            "active_alerts": len(self.alerts.get_active()),
        }

    def export(self, name: str, path: str) -> str:
        points = self.store.get_series(name)
        data = [{"t": p.timestamp, "v": p.value, "tags": p.tags} for p in points]
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== Analytics Engine Demo ===\n")
    engine = AnalyticsEngine()

    # Generate sample data
    import random
    for i in range(100):
        engine.record("cpu_usage", 20 + random.gauss(0, 5) + (i / 10))
        engine.record("memory_usage", 50 + random.gauss(0, 10))
        time.sleep(0.001)

    print(f"Series: {engine.store.list_series()}")
    print(f"CPU stats: {engine.store.stats('cpu_usage')}")
    print(f"Memory stats: {engine.store.stats('memory_usage')}")

    print("\nAggregated CPU (10s windows, mean):")
    agg = engine.aggregate("cpu_usage", window=10, func="mean")
    for a in agg[:5]:
        print(f"  {a['window_start']}: {a['value']:.2f} (n={a['count']})")

    print("\nAnomaly detection:")
    anomalies = engine.detector.detect("cpu_usage", method="zscore", threshold=2.0)
    print(f"  Found {len(anomalies)} anomalies")

    print("\nAlert rules:")
    alert_id = engine.add_alert("cpu_usage", ">", 30, duration=5, severity="warning")
    print(f"  Added alert: {alert_id}")
    engine.alerts.check_all()
    print(f"  Active alerts: {len(engine.alerts.get_active())}")

    print(f"\nEngine stats: {engine.stats()}")


if __name__ == "__main__":
    _demo()
