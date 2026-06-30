#!/usr/bin/env python3
"""
metrics_collector_native.py
MAGNATRIX-OS — Native Metrics Collector

Time-series metrics aggregation (counters, gauges, histograms), health telemetry exporter,
alert thresholds. Feeds dashboard_production with live data. Prometheus-like but pure Python.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations

import json
import statistics
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable


@dataclass
class Metric:
    """A single metric sample."""
    name: str
    value: float
    metric_type: str = "gauge"  # counter, gauge, histogram
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MetricsCollectorNative:
    """
    Time-series metrics collector with counters, gauges, histograms.
    Alert thresholds, health telemetry export. Pure stdlib.
    """

    def __init__(self, workspace: str = "./metrics") -> None:
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._metrics: List[Metric] = []
        self._lock = threading.RLock()
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._thresholds: Dict[str, Dict[str, Any]] = {}
        self._alert_handlers: List[Callable[[str, Dict[str, Any]], None]] = []
        self._running = False
        self._flush_thread: Optional[threading.Thread] = None
        self._flush_interval: int = 60
        self._persist_path = self.workspace / "metrics.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            try:
                with open(self._persist_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for m in data:
                    self._metrics.append(Metric(**m))
            except Exception:
                pass

    def _save(self) -> None:
        with open(self._persist_path, "w", encoding="utf-8") as f:
            json.dump([asdict(m) for m in self._metrics[-5000:]], f, indent=2)  # Keep last 5000

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
            self._flush_thread.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False
            self._save()

    def _flush_loop(self) -> None:
        while self._running:
            time.sleep(self._flush_interval)
            self._save()
            self._check_alerts()

    def counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter."""
        with self._lock:
            key = self._key(name, labels)
            self._counters[key] = self._counters.get(key, 0) + value
            self._metrics.append(Metric(name=name, value=self._counters[key], metric_type="counter", labels=labels or {}))

    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge value."""
        with self._lock:
            key = self._key(name, labels)
            self._gauges[key] = value
            self._metrics.append(Metric(name=name, value=value, metric_type="gauge", labels=labels or {}))

    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram observation."""
        with self._lock:
            key = self._key(name, labels)
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)
            self._metrics.append(Metric(name=name, value=value, metric_type="histogram", labels=labels or {}))

    def _key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name

    def set_threshold(self, name: str, min_val: Optional[float] = None,
                      max_val: Optional[float] = None, labels: Optional[Dict[str, str]] = None) -> None:
        """Set alert thresholds for a metric."""
        with self._lock:
            self._thresholds[name] = {
                "min": min_val,
                "max": max_val,
                "labels": labels or {},
            }

    def add_alert_handler(self, handler: Callable[[str, Dict[str, Any]], None]) -> None:
        self._alert_handlers.append(handler)

    def _check_alerts(self) -> None:
        for name, threshold in self._thresholds.items():
            latest = self._get_latest(name)
            if latest is None:
                continue
            alerts = []
            if threshold["min"] is not None and latest < threshold["min"]:
                alerts.append(f"{name} below threshold: {latest} < {threshold['min']}")
            if threshold["max"] is not None and latest > threshold["max"]:
                alerts.append(f"{name} above threshold: {latest} > {threshold['max']}")
            for alert in alerts:
                for handler in self._alert_handlers:
                    try:
                        handler(alert, {"metric": name, "value": latest, "threshold": threshold})
                    except Exception:
                        pass

    def _get_latest(self, name: str) -> Optional[float]:
        for m in reversed(self._metrics):
            if m.name == name:
                return m.value
        return None

    def get_summary(self, name: str, metric_type: Optional[str] = None,
                    labels: Optional[Dict[str, str]] = None, window: int = 3600) -> Dict[str, Any]:
        """Get summary statistics for a metric."""
        now = time.time()
        with self._lock:
            values = [m.value for m in self._metrics
                      if m.name == name
                      and (metric_type is None or m.metric_type == metric_type)
                      and (labels is None or m.labels == labels)
                      and m.timestamp >= now - window]
            if not values:
                return {"name": name, "count": 0, "status": "no_data"}
            return {
                "name": name,
                "count": len(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
                "min": min(values),
                "max": max(values),
                "status": "ok",
            }

    def export_prometheus(self, path: Optional[str] = None) -> str:
        """Export metrics in Prometheus text format."""
        export_path = Path(path) if path else self.workspace / f"prometheus_{int(time.time())}.txt"
        lines = []
        with self._lock:
            # Counters
            for key, val in self._counters.items():
                lines.append(f"# TYPE {key.split('{')[0]} counter")
                lines.append(f"{key} {val}")
            # Gauges
            for key, val in self._gauges.items():
                lines.append(f"# TYPE {key.split('{')[0]} gauge")
                lines.append(f"{key} {val}")
            # Histograms
            for key, vals in self._histograms.items():
                if vals:
                    lines.append(f"# TYPE {key.split('{')[0]} histogram")
                    lines.append(f"{key}_count {len(vals)}")
                    lines.append(f"{key}_sum {sum(vals)}")
                    try:
                        lines.append(f"{key}_avg {statistics.mean(vals)}")
                    except Exception:
                        pass
        with open(export_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return str(export_path)

    def export_health_telemetry(self) -> Dict[str, Any]:
        """Export health telemetry for dashboard consumption."""
        with self._lock:
            return {
                "timestamp": time.time(),
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {k: {"count": len(v), "sum": sum(v), "avg": statistics.mean(v) if v else 0}
                              for k, v in self._histograms.items()},
                "thresholds": self._thresholds,
                "total_samples": len(self._metrics),
            }

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "total_samples": len(self._metrics),
                "counters": len(self._counters),
                "gauges": len(self._gauges),
                "histograms": len(self._histograms),
                "thresholds": len(self._thresholds),
                "workspace": str(self.workspace),
            }
