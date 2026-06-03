"""
llm_rate_analytics_native.py
MAGNATRIX-OS Rate Analytics Engine
Native Python, stdlib only.
Provides rate analysis, throughput metrics, latency distribution, and performance benchmarking.
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class RateSample:
    timestamp: float
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"timestamp": self.timestamp, "value": self.value}


class RateAnalyticsEngine:
    """Rate and throughput analytics with distribution analysis."""

    def __init__(self) -> None:
        self._samples: Dict[str, List[RateSample]] = {}

    def record(self, metric_name: str, value: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        if metric_name not in self._samples:
            self._samples[metric_name] = []
        self._samples[metric_name].append(RateSample(timestamp=time.time(), value=value, metadata=metadata or {}))

    def get_stats(self, metric_name: str) -> Dict[str, Any]:
        samples = self._samples.get(metric_name, [])
        if not samples:
            return {}
        values = [s.value for s in samples]
        return {
            "count": len(values), "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values), "max": max(values),
            "p95": sorted(values)[int(len(values) * 0.95)] if values else 0,
            "p99": sorted(values)[int(len(values) * 0.99)] if values else 0,
        }

    def get_throughput(self, metric_name: str, window_seconds: float = 60.0) -> float:
        now = time.time()
        samples = self._samples.get(metric_name, [])
        recent = [s for s in samples if s.timestamp >= now - window_seconds]
        return len(recent) / window_seconds if window_seconds > 0 else 0.0

    def get_trend(self, metric_name: str, periods: int = 5) -> List[float]:
        samples = self._samples.get(metric_name, [])
        if not samples:
            return []
        # Split into periods and return average per period
        total_time = samples[-1].timestamp - samples[0].timestamp if len(samples) > 1 else 1
        period_length = total_time / periods if periods > 0 else 1
        trends = []
        for i in range(periods):
            start = samples[0].timestamp + i * period_length
            end = start + period_length
            period_samples = [s.value for s in samples if start <= s.timestamp < end]
            trends.append(statistics.mean(period_samples) if period_samples else 0.0)
        return trends

    def compare_metrics(self, metric_a: str, metric_b: str) -> Dict[str, Any]:
        stats_a = self.get_stats(metric_a)
        stats_b = self.get_stats(metric_b)
        return {
            "metric_a": stats_a, "metric_b": stats_b,
            "difference_mean": stats_a.get("mean", 0) - stats_b.get("mean", 0),
        }

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        return {k: self.get_stats(k) for k in self._samples.keys()}

    def clear(self, metric_name: Optional[str] = None) -> None:
        if metric_name:
            self._samples.pop(metric_name, None)
        else:
            self._samples.clear()


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Rate Analytics Engine")
    print("=" * 60)

    engine = RateAnalyticsEngine()

    print("\n--- Record samples ---")
    for i in range(100):
        engine.record("latency_ms", 50 + (i % 20) * 5)
        engine.record("requests_per_sec", 10 + (i % 10))

    print("\n--- Latency stats ---")
    print(engine.get_stats("latency_ms"))

    print("\n--- Throughput ---")
    print(f"  requests_per_sec throughput: {engine.get_throughput('requests_per_sec', 60):.2f}/s")

    print("\n--- Trend ---")
    trend = engine.get_trend("latency_ms", periods=5)
    print(f"  Latency trend: {trend}")

    print("\n--- All stats ---")
    for metric, stats in engine.get_all_stats().items():
        print(f"  {metric}: count={stats['count']}, mean={stats['mean']:.2f}")

    print("\nRate Analytics test complete.")


if __name__ == "__main__":
    run()
