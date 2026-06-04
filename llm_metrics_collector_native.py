"""Metrics Collector — counters, gauges, histograms, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import time
import math

class MetricType(Enum):
    COUNTER = auto()
    GAUGE = auto()
    HISTOGRAM = auto()

@dataclass
class Metric:
    name: str
    metric_type: MetricType
    labels: Dict[str, str] = field(default_factory=dict)
    value: float = 0.0
    histogram_values: List[float] = field(default_factory=list)

class MetricsCollector:
    def __init__(self):
        self.metrics: Dict[str, Metric] = {}
        self.registry: Dict[str, Dict] = {}

    def counter(self, name: str, labels: Dict = None) -> Metric:
        key = self._key(name, labels)
        if key not in self.metrics:
            self.metrics[key] = Metric(name, MetricType.COUNTER, labels or {})
        return self.metrics[key]

    def gauge(self, name: str, labels: Dict = None) -> Metric:
        key = self._key(name, labels)
        if key not in self.metrics:
            self.metrics[key] = Metric(name, MetricType.GAUGE, labels or {})
        return self.metrics[key]

    def histogram(self, name: str, labels: Dict = None) -> Metric:
        key = self._key(name, labels)
        if key not in self.metrics:
            self.metrics[key] = Metric(name, MetricType.HISTOGRAM, labels or {})
        return self.metrics[key]

    def _key(self, name: str, labels: Dict) -> str:
        return name + ":" + str(sorted(labels.items())) if labels else name

    def inc(self, name: str, value: float = 1.0, labels: Dict = None):
        m = self.counter(name, labels)
        m.value += value

    def dec(self, name: str, value: float = 1.0, labels: Dict = None):
        m = self.counter(name, labels)
        m.value -= value

    def set(self, name: str, value: float, labels: Dict = None):
        m = self.gauge(name, labels)
        m.value = value

    def observe(self, name: str, value: float, labels: Dict = None):
        m = self.histogram(name, labels)
        m.histogram_values.append(value)

    def summary(self, name: str, labels: Dict = None) -> Dict:
        key = self._key(name, labels)
        m = self.metrics.get(key)
        if not m:
            return {}
        if m.metric_type == MetricType.HISTOGRAM and m.histogram_values:
            vals = sorted(m.histogram_values)
            return {"count": len(vals), "sum": sum(vals), "avg": sum(vals)/len(vals), "p50": vals[len(vals)//2], "p95": vals[int(len(vals)*0.95)] if len(vals) > 1 else vals[0]}
        return {"name": name, "type": m.metric_type.name, "value": m.value, "labels": m.labels}

    def stats(self) -> Dict:
        return {"metrics": len(self.metrics), "by_type": {t.name: sum(1 for m in self.metrics.values() if m.metric_type == t) for t in MetricType}}

def run():
    collector = MetricsCollector()
    collector.inc("requests", 1, {"method": "GET"})
    collector.inc("requests", 2, {"method": "POST"})
    collector.set("cpu_usage", 45.0)
    for v in [10, 20, 30, 40, 50]:
        collector.observe("latency", v)
    print(collector.summary("requests", {"method": "GET"}))
    print(collector.summary("latency"))
    print(collector.stats())

if __name__ == "__main__":
    run()
