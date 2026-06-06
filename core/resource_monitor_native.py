#!/usr/bin/env python3
"""
Resource Monitor for MAGNATRIX-OS
CPU, memory, disk, and network monitoring with thresholds,
alerts, and historical tracking. Native stdlib only (psutil-like via /proc).

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class MetricType(enum.Enum):
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    LOAD = "load"


class ThresholdSeverity(enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclasses.dataclass
class MetricSnapshot:
    metric_type: MetricType
    value: float
    unit: str
    timestamp: float
    details: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.metric_type.value,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp,
            "details": self.details,
        }


@dataclasses.dataclass
class ThresholdRule:
    metric_type: MetricType
    name: str
    warning: float
    critical: float
    direction: str = "above"  # above or below

    def check(self, value: float) -> Optional[ThresholdSeverity]:
        if self.direction == "above":
            if value >= self.critical:
                return ThresholdSeverity.CRITICAL
            if value >= self.warning:
                return ThresholdSeverity.WARNING
        else:
            if value <= self.critical:
                return ThresholdSeverity.CRITICAL
            if value <= self.warning:
                return ThresholdSeverity.WARNING
        return None


class ResourceMonitor:
    """System resource monitoring with threshold-based alerting."""

    def __init__(self, history_limit: int = 1000) -> None:
        self.history_limit = history_limit
        self._history: List[MetricSnapshot] = []
        self._thresholds: List[ThresholdRule] = []
        self._alerts: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Metric collection
    # ------------------------------------------------------------------

    def get_cpu_percent(self) -> MetricSnapshot:
        """Read CPU usage from /proc/stat (Linux)."""
        try:
            with open("/proc/stat", "r") as f:
                line = f.readline()
            fields = list(map(int, line.split()[1:]))
            idle = fields[3]
            total = sum(fields)
            usage = ((total - idle) / total * 100) if total > 0 else 0
        except Exception:
            usage = 0.0
        return MetricSnapshot(MetricType.CPU, round(usage, 2), "%", time.time(), {"cores": os.cpu_count()})

    def get_memory_info(self) -> MetricSnapshot:
        """Read memory from /proc/meminfo (Linux)."""
        try:
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
            mem_total = 0
            mem_available = 0
            for line in lines:
                if line.startswith("MemTotal:"):
                    mem_total = int(line.split()[1]) * 1024
                elif line.startswith("MemAvailable:"):
                    mem_available = int(line.split()[1]) * 1024
            used = mem_total - mem_available
            percent = (used / mem_total * 100) if mem_total > 0 else 0
        except Exception:
            mem_total = used = percent = 0
        return MetricSnapshot(MetricType.MEMORY, round(percent, 2), "%", time.time(), {
            "total": mem_total, "used": used, "unit": "bytes"
        })

    def get_disk_info(self, path: str = "/") -> MetricSnapshot:
        try:
            stat = os.statvfs(path)
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bavail * stat.f_frsize
            used = total - free
            percent = (used / total * 100) if total > 0 else 0
        except Exception:
            total = free = used = percent = 0
        return MetricSnapshot(MetricType.DISK, round(percent, 2), "%", time.time(), {
            "total": total, "free": free, "used": used, "path": path, "unit": "bytes"
        })

    def get_load_avg(self) -> MetricSnapshot:
        try:
            load1, load5, load15 = os.getloadavg()
        except Exception:
            load1 = load5 = load15 = 0.0
        return MetricSnapshot(MetricType.LOAD, round(load1, 2), "", time.time(), {
            "load_1min": load1, "load_5min": load5, "load_15min": load15
        })

    def get_all_metrics(self) -> List[MetricSnapshot]:
        return [
            self.get_cpu_percent(),
            self.get_memory_info(),
            self.get_disk_info(),
            self.get_load_avg(),
        ]

    def snapshot(self) -> Dict[str, Any]:
        metrics = self.get_all_metrics()
        self._history.extend(metrics)
        if len(self._history) > self.history_limit:
            self._history = self._history[-self.history_limit:]
        # Check thresholds
        for m in metrics:
            for rule in self._thresholds:
                if rule.metric_type == m.metric_type:
                    severity = rule.check(m.value)
                    if severity:
                        self._alerts.append({
                            "timestamp": time.time(),
                            "metric": m.metric_type.value,
                            "value": m.value,
                            "rule": rule.name,
                            "severity": severity.value,
                        })
        return {m.metric_type.value: m.to_dict() for m in metrics}

    # ------------------------------------------------------------------
    # Threshold management
    # ------------------------------------------------------------------

    def add_threshold(self, rule: ThresholdRule) -> None:
        self._thresholds.append(rule)

    def list_thresholds(self) -> List[ThresholdRule]:
        return self._thresholds

    def get_alerts(self, severity: Optional[ThresholdSeverity] = None, limit: int = 100) -> List[Dict[str, Any]]:
        alerts = self._alerts
        if severity:
            alerts = [a for a in alerts if a["severity"] == severity.value]
        return alerts[-limit:]

    def clear_alerts(self) -> None:
        self._alerts.clear()

    # ------------------------------------------------------------------
    # Historical data
    # ------------------------------------------------------------------

    def get_history(self, metric_type: MetricType, limit: int = 100) -> List[MetricSnapshot]:
        filtered = [m for m in self._history if m.metric_type == metric_type]
        return filtered[-limit:]

    def get_avg(self, metric_type: MetricType, window_seconds: float = 300) -> float:
        now = time.time()
        values = [m.value for m in self._history if m.metric_type == metric_type and now - m.timestamp < window_seconds]
        return sum(values) / len(values) if values else 0.0

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        by_type = {}
        for m in self._history:
            by_type[m.metric_type.value] = by_type.get(m.metric_type.value, 0) + 1
        return {
            "total_snapshots": len(self._history) // 4,
            "history_entries": len(self._history),
            "thresholds": len(self._thresholds),
            "alerts": len(self._alerts),
            "by_type": by_type,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    monitor = ResourceMonitor(history_limit=500)
    print("=== Resource Monitor Demo ===\n")
    # Add thresholds
    monitor.add_threshold(ThresholdRule(MetricType.CPU, "cpu_warning", warning=70, critical=90))
    monitor.add_threshold(ThresholdRule(MetricType.MEMORY, "mem_warning", warning=80, critical=95))
    # Take snapshot
    snap = monitor.snapshot()
    for k, v in snap.items():
        print(f"{k}: {v['value']}{v['unit']} ({v['details']})")
    # History
    print(f"\nHistory: {len(monitor._history)} entries")
    # Alerts
    alerts = monitor.get_alerts()
    if alerts:
        print(f"Alerts: {len(alerts)}")
        for a in alerts[:5]:
            print(f"  [{a['severity']}] {a['metric']} = {a['value']}")
    # Stats
    print(f"\nStats: {monitor.stats()}")


if __name__ == "__main__":
    _demo()
