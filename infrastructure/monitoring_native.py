"""infrastructure/monitoring_native.py — Monitoring and observability"""
from __future__ import annotations
import statistics
import time
from typing import Any, Dict, List, Optional

class MonitoringSystem:
    """Monitoring system with metrics and alerts."""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.alerts: List[Dict[str, Any]] = []
        self.rules: Dict[str, Dict[str, Any]] = {}

    def record(self, name: str, value: float) -> None:
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(value)
        self._check_alerts(name, value)

    def counter(self, name: str, increment: int = 1) -> None:
        self.record(name, float(increment))

    def gauge(self, name: str, value: float) -> None:
        self.record(name, value)

    def histogram(self, name: str, value: float) -> None:
        self.record(name, value)

    def add_alert_rule(self, name: str, metric: str, threshold: float, comparison: str = "above") -> None:
        self.rules[name] = {
            "metric": metric,
            "threshold": threshold,
            "comparison": comparison,
        }

    def _check_alerts(self, metric: str, value: float) -> None:
        for rule_name, rule in self.rules.items():
            if rule["metric"] != metric:
                continue
            triggered = False
            if rule["comparison"] == "above" and value > rule["threshold"]:
                triggered = True
            elif rule["comparison"] == "below" and value < rule["threshold"]:
                triggered = True

            if triggered:
                self.alerts.append({
                    "rule": rule_name,
                    "metric": metric,
                    "value": value,
                    "threshold": rule["threshold"],
                    "timestamp": time.time(),
                })

    def get_stats(self, metric: str) -> Dict[str, Any]:
        values = self.metrics.get(metric, [])
        if not values:
            return {}
        return {
            "count": len(values),
            "sum": sum(values),
            "mean": statistics.mean(values),
            "min": min(values),
            "max": max(values),
        }

    def get_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.alerts[-limit:]

if __name__ == "__main__":
    print("MonitoringSystem self-test")
    ms = MonitoringSystem()
    ms.add_alert_rule("cpu_high", "cpu", 80.0)
    ms.gauge("cpu", 85.0)
    assert len(ms.get_alerts()) == 1
    print("All tests pass")
