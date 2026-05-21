#!/usr/bin/env python3
"""
telemetry.py — Telemetry & Monitoring MAGNATRIX
Batch Super AI — Infrastructure Core

Collect, analyze, and alert on system metrics across all engines.
"""
import json
import os
import random
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


@dataclass
class MetricSnapshot:
    timestamp: str
    engine_name: str
    cpu_percent: float
    memory_mb: float
    latency_ms: float
    error_rate: float
    throughput: float
    custom: Dict[str, float] = field(default_factory=dict)


@dataclass
class DegradationAlert:
    alert_id: str
    engine_name: str
    metric_name: str
    expected: float
    actual: float
    severity: str
    timestamp: str


class TelemetryCollector:
    """Collect metrics from all MAGNATRIX engines."""

    def __init__(self, baseline_window: int = 10):
        self.baseline_window = baseline_window
        self.history: Dict[str, List[MetricSnapshot]] = {}
        self.baselines: Dict[str, Dict[str, float]] = {}
        self.alerts: List[DegradationAlert] = []
        self.alert_thresholds = {
            "cpu_percent": 0.80,
            "memory_mb": 512.0,
            "latency_ms": 500.0,
            "error_rate": 0.05,
        }

    def collect_metrics(self, engine_name: str, metrics: Dict[str, float]) -> MetricSnapshot:
        """Collect a metric snapshot from an engine."""
        snapshot = MetricSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            engine_name=engine_name,
            cpu_percent=metrics.get("cpu_percent", 0.0),
            memory_mb=metrics.get("memory_mb", 0.0),
            latency_ms=metrics.get("latency_ms", 0.0),
            error_rate=metrics.get("error_rate", 0.0),
            throughput=metrics.get("throughput", 0.0),
            custom={k: v for k, v in metrics.items() if k not in {
                "cpu_percent", "memory_mb", "latency_ms", "error_rate", "throughput"
            }},
        )
        self.history.setdefault(engine_name, []).append(snapshot)
        if len(self.history[engine_name]) > 1000:
            self.history[engine_name].pop(0)
        self._update_baseline(engine_name)
        return snapshot

    def _update_baseline(self, engine_name: str):
        """Update rolling baseline for an engine."""
        arr = self.history.get(engine_name, [])
        if len(arr) < 3:
            return
        window = arr[-self.baseline_window:]
        self.baselines[engine_name] = {
            "cpu_percent": sum(s.cpu_percent for s in window) / len(window),
            "memory_mb": sum(s.memory_mb for s in window) / len(window),
            "latency_ms": sum(s.latency_ms for s in window) / len(window),
            "error_rate": sum(s.error_rate for s in window) / len(window),
            "throughput": sum(s.throughput for s in window) / len(window),
        }

    def detect_degradation(self) -> List[DegradationAlert]:
        """Detect if any metric has degraded from baseline."""
        alerts = []
        for engine_name, baseline in self.baselines.items():
            arr = self.history.get(engine_name, [])
            if not arr:
                continue
            latest = arr[-1]

            checks = [
                ("cpu_percent", latest.cpu_percent, baseline["cpu_percent"], 1.5),
                ("memory_mb", latest.memory_mb, baseline["memory_mb"], 1.5),
                ("latency_ms", latest.latency_ms, baseline["latency_ms"], 2.0),
                ("error_rate", latest.error_rate, baseline["error_rate"], 3.0),
            ]

            for metric_name, actual, expected, multiplier in checks:
                threshold = expected * multiplier if expected > 0 else self.alert_thresholds[metric_name]
                if actual > threshold:
                    severity = "medium"
                    if actual > threshold * 1.5:
                        severity = "critical"
                    elif actual > threshold * 1.2:
                        severity = "high"

                    alert = DegradationAlert(
                        alert_id=f"alert-{engine_name}-{metric_name}-{int(time.time())}",
                        engine_name=engine_name,
                        metric_name=metric_name,
                        expected=round(expected, 3),
                        actual=round(actual, 3),
                        severity=severity,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                    self.alerts.append(alert)
                    alerts.append(alert)

        return alerts

    def generate_dashboard_data(self) -> Dict[str, Any]:
        """Format data for external dashboard visualization."""
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "engines": {},
            "alerts": [],
            "summary": {},
        }

        for engine_name, snapshots in self.history.items():
            if not snapshots:
                continue
            latest = snapshots[-1]
            baseline = self.baselines.get(engine_name, {})
            data["engines"][engine_name] = {
                "current": asdict(latest),
                "baseline": baseline,
                "history_length": len(snapshots),
            }

        data["alerts"] = [asdict(a) for a in self.alerts[-20:]]

        # Summary stats
        all_cpu = [s.cpu_percent for snaps in self.history.values() for s in snaps[-5:]]
        all_lat = [s.latency_ms for snaps in self.history.values() for s in snaps[-5:]]
        data["summary"] = {
            "total_engines": len(self.history),
            "avg_cpu": round(sum(all_cpu) / len(all_cpu), 2) if all_cpu else 0,
            "avg_latency_ms": round(sum(all_lat) / len(all_lat), 2) if all_lat else 0,
            "total_alerts": len(self.alerts),
            "critical_alerts": sum(1 for a in self.alerts if a.severity == "critical"),
        }

        return data

    def alert_if_critical(self) -> List[str]:
        """Return critical alert messages."""
        critical = [a for a in self.alerts if a.severity == "critical"]
        return [
            f"🚨 CRITICAL: {a.engine_name}.{a.metric_name} = {a.actual} (expected {a.expected})"
            for a in critical[-5:]
        ]

    def export_csv(self, engine_name: Optional[str] = None) -> str:
        """Export metrics to CSV format."""
        lines = ["timestamp,engine,cpu_percent,memory_mb,latency_ms,error_rate,throughput"]
        targets = [engine_name] if engine_name else list(self.history.keys())
        for name in targets:
            for s in self.history.get(name, []):
                lines.append(f"{s.timestamp},{s.engine_name},{s.cpu_percent},{s.memory_mb},{s.latency_ms},{s.error_rate},{s.throughput}")
        return "\n".join(lines)

    def get_health_score(self, engine_name: str) -> float:
        """Compute 0-1 health score for an engine."""
        arr = self.history.get(engine_name, [])
        if not arr:
            return 0.0
        latest = arr[-1]
        score = 1.0
        score -= min(0.5, latest.cpu_percent)
        score -= min(0.3, latest.error_rate * 10)
        score -= min(0.2, latest.latency_ms / 1000)
        return max(0.0, score)


# ── demo ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 70)
    print("MAGNATRIX Telemetry — Monitoring & Alerting")
    print("=" * 70)

    telem = TelemetryCollector()

    # Simulate collecting metrics from multiple engines
    engines = ["swarm", "trading", "knowledge", "security", "brain"]
    for _ in range(15):
        for engine in engines:
            metrics = {
                "cpu_percent": random.uniform(0.1, 0.95),
                "memory_mb": random.uniform(64, 800),
                "latency_ms": random.uniform(10, 800),
                "error_rate": random.uniform(0.0, 0.08),
                "throughput": random.uniform(100, 5000),
            }
            telem.collect_metrics(engine, metrics)

    print(f"\n[1] COLLECTED METRICS")
    print(f"    Engines monitored: {len(telem.history)}")
    for name, snaps in telem.history.items():
        print(f"    {name}: {len(snaps)} snapshots")

    print(f"\n[2] BASELINES")
    for name, baseline in telem.baselines.items():
        print(f"    {name}: cpu={baseline['cpu_percent']:.2f}, latency={baseline['latency_ms']:.1f}ms")

    print(f"\n[3] DEGRADATION DETECTION")
    alerts = telem.detect_degradation()
    if alerts:
        for a in alerts:
            print(f"    ⚠️  [{a.severity.upper()}] {a.engine_name}.{a.metric_name}: {a.actual:.2f} (baseline {a.expected:.2f})")
    else:
        print("    ✅ All metrics within normal range")

    print(f"\n[4] CRITICAL ALERTS")
    critical = telem.alert_if_critical()
    if critical:
        for msg in critical:
            print(f"    {msg}")
    else:
        print("    ✅ No critical alerts")

    print(f"\n[5] DASHBOARD DATA (summary)")
    dash = telem.generate_dashboard_data()
    print(f"    Engines: {dash['summary']['total_engines']}")
    print(f"    Avg CPU: {dash['summary']['avg_cpu']}%")
    print(f"    Avg Latency: {dash['summary']['avg_latency_ms']}ms")
    print(f"    Total Alerts: {dash['summary']['total_alerts']}")

    print(f"\n[6] HEALTH SCORES")
    for engine in engines:
        score = telem.get_health_score(engine)
        bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
        print(f"    [{bar}] {engine:15s} {score:.2f}")

    print(f"\n[7] CSV EXPORT (first 3 lines)")
    csv = telem.export_csv()
    for line in csv.split("\n")[:4]:
        print(f"    {line}")

    print("\n" + "=" * 70)
    print("Telemetry demo selesai.")
    print("=" * 70)
