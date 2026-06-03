"""LLM Metrics Collector — Native Python (stdlib only)."""
from __future__ import annotations
import time, json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto
from collections import deque

class MetricType(Enum):
    COUNTER = auto()
    GAUGE = auto()
    HISTOGRAM = auto()
    SUMMARY = auto()

@dataclass
class MetricValue:
    name: str
    metric_type: MetricType
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)

class MetricsCollector:
    def __init__(self, max_history: int = 1000) -> None:
        self._metrics: Dict[str, deque] = {}
        self._max_history = max_history

    def record(self, metric: MetricValue) -> None:
        if metric.name not in self._metrics:
            self._metrics[metric.name] = deque(maxlen=self._max_history)
        self._metrics[metric.name].append(metric)

    def increment(self, name: str, labels: Optional[Dict[str, str]] = None, value: float = 1.0) -> None:
        self.record(MetricValue(name, MetricType.COUNTER, value, time.time(), labels or {}))

    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        self.record(MetricValue(name, MetricType.GAUGE, value, time.time(), labels or {}))

    def get_latest(self, name: str) -> Optional[MetricValue]:
        values = self._metrics.get(name)
        return values[-1] if values else None

    def get_average(self, name: str, window: int = 100) -> float:
        values = list(self._metrics.get(name, []))[-window:]
        if not values:
            return 0.0
        return sum(v.value for v in values) / len(values)

    def get_stats(self) -> Dict[str, Any]:
        return {"metrics": len(self._metrics), "total_samples": sum(len(v) for v in self._metrics.values())}

def run() -> None:
    print("Metrics Collector test")
    e = MetricsCollector()
    e.increment("requests", {"endpoint": "/chat"}, 1)
    e.increment("requests", {"endpoint": "/chat"}, 1)
    e.gauge("latency", 0.045, {"endpoint": "/chat"})
    e.gauge("latency", 0.052, {"endpoint": "/chat"})
    print("  Latest latency: " + str(e.get_latest("latency").value))
    print("  Avg latency: " + str(e.get_average("latency")))
    print("  Stats: " + str(e.get_stats()))
    print("Metrics Collector test complete.")

if __name__ == "__main__":
    run()
