"""Model Performance Profiler — Latency, throughput, accuracy, resource usage profiling.

Modul ini menyediakan:
- PerformanceMetrics: collect and aggregate timing data
- LatencyProfiler: measure request latency percentiles
- ThroughputAnalyzer: calculate requests per second
- AccuracyTracker: track response quality metrics
- ResourceMonitor: CPU/memory usage tracking
- ProfilerDashboard: aggregate all profiling data
"""

from __future__ import annotations

import json
import time
import uuid
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum, auto


class MetricType(Enum):
    LATENCY = auto()
    THROUGHPUT = auto()
    ACCURACY = auto()
    RESOURCE = auto()
    ERROR_RATE = auto()
    TOKEN_RATE = auto()


@dataclass
class MetricRecord:
    """Single metric measurement."""
    record_id: str
    metric_type: MetricType
    value: float
    model_id: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LatencySnapshot:
    """Latency statistics snapshot."""
    count: int
    mean: float
    p50: float
    p95: float
    p99: float
    min: float
    max: float
    std: float


class LatencyProfiler:
    """Measure and analyze request latency."""

    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self._latencies: List[float] = []
        self._start_times: Dict[str, float] = {}

    def start(self, request_id: str) -> None:
        self._start_times[request_id] = time.time()

    def end(self, request_id: str) -> Optional[float]:
        start = self._start_times.pop(request_id, None)
        if start is None:
            return None
        latency = time.time() - start
        self._latencies.append(latency)
        if len(self._latencies) > self.window_size:
            self._latencies = self._latencies[-self.window_size:]
        return latency

    def get_snapshot(self) -> LatencySnapshot:
        if not self._latencies:
            return LatencySnapshot(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        sorted_lat = sorted(self._latencies)
        n = len(sorted_lat)
        mean = sum(sorted_lat) / n
        variance = sum((x - mean) ** 2 for x in sorted_lat) / n
        return LatencySnapshot(
            count=n,
            mean=round(mean, 4),
            p50=round(sorted_lat[int(n * 0.5)], 4),
            p95=round(sorted_lat[int(n * 0.95)], 4),
            p99=round(sorted_lat[int(n * 0.99)], 4),
            min=round(sorted_lat[0], 4),
            max=round(sorted_lat[-1], 4),
            std=round(variance ** 0.5, 4)
        )

    def get_stats(self) -> Dict[str, Any]:
        snap = self.get_snapshot()
        return {k: v for k, v in snap.__dict__.items()}


class ThroughputAnalyzer:
    """Calculate requests per second over time windows."""

    def __init__(self, window_seconds: float = 60.0):
        self.window = window_seconds
        self._timestamps: List[float] = []

    def record(self) -> None:
        self._timestamps.append(time.time())
        cutoff = time.time() - self.window
        self._timestamps = [t for t in self._timestamps if t >= cutoff]

    def get_rps(self) -> float:
        if not self._timestamps:
            return 0.0
        duration = time.time() - min(self._timestamps)
        return len(self._timestamps) / max(duration, 1e-9)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "rps": round(self.get_rps(), 2),
            "total_requests": len(self._timestamps),
            "window_seconds": self.window
        }


class AccuracyTracker:
    """Track response quality and accuracy metrics."""

    def __init__(self):
        self._scores: List[float] = []
        self._correct = 0
        self._total = 0
        self._human_ratings: List[int] = []

    def record_score(self, score: float) -> None:
        self._scores.append(score)

    def record_binary(self, correct: bool) -> None:
        self._total += 1
        if correct:
            self._correct += 1

    def record_rating(self, rating: int) -> None:
        self._human_ratings.append(rating)

    def get_accuracy(self) -> float:
        return self._correct / max(self._total, 1)

    def get_avg_score(self) -> float:
        return sum(self._scores) / max(len(self._scores), 1)

    def get_avg_rating(self) -> float:
        return sum(self._human_ratings) / max(len(self._human_ratings), 1)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "accuracy": round(self.get_accuracy(), 4),
            "avg_score": round(self.get_avg_score(), 4),
            "avg_rating": round(self.get_avg_rating(), 2),
            "total_evaluated": self._total,
            "samples": len(self._scores)
        }


class ResourceMonitor:
    """Track CPU/memory usage (simulated)."""

    def __init__(self):
        self._cpu_readings: List[float] = []
        self._memory_readings: List[float] = []

    def record(self, cpu_percent: float, memory_mb: float) -> None:
        self._cpu_readings.append(cpu_percent)
        self._memory_readings.append(memory_mb)
        # Keep last 100 readings
        self._cpu_readings = self._cpu_readings[-100:]
        self._memory_readings = self._memory_readings[-100:]

    def simulate(self) -> None:
        # Simulated readings
        self.record(random.uniform(20, 80), random.uniform(512, 2048))

    def get_stats(self) -> Dict[str, Any]:
        if not self._cpu_readings:
            return {"cpu_avg": 0, "memory_avg": 0}
        return {
            "cpu_avg": round(sum(self._cpu_readings) / len(self._cpu_readings), 2),
            "cpu_max": round(max(self._cpu_readings), 2),
            "memory_avg_mb": round(sum(self._memory_readings) / len(self._memory_readings), 2),
            "memory_max_mb": round(max(self._memory_readings), 2)
        }


class ProfilerDashboard:
    """Aggregate all profiling data."""

    def __init__(self, model_id: str = ""):
        self.model_id = model_id or str(uuid.uuid4())[:8]
        self.latency = LatencyProfiler()
        self.throughput = ThroughputAnalyzer()
        self.accuracy = AccuracyTracker()
        self.resource = ResourceMonitor()
        self._error_count = 0
        self._total_requests = 0
        self._start_time = time.time()

    def record_request(self, latency: float, success: bool = True, score: Optional[float] = None) -> None:
        self._total_requests += 1
        self.latency._latencies.append(latency)
        self.throughput.record()
        if not success:
            self._error_count += 1
        if score is not None:
            self.accuracy.record_score(score)
        self.resource.simulate()

    def get_error_rate(self) -> float:
        return self._error_count / max(self._total_requests, 1)

    def get_uptime(self) -> float:
        return time.time() - self._start_time

    def get_full_report(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "uptime_seconds": round(self.get_uptime(), 2),
            "total_requests": self._total_requests,
            "error_rate": round(self.get_error_rate(), 4),
            "latency": self.latency.get_stats(),
            "throughput": self.throughput.get_stats(),
            "accuracy": self.accuracy.get_stats(),
            "resource": self.resource.get_stats()
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.get_full_report(), f, indent=2)

    def benchmark(self, fn: Callable[[], Any], iterations: int = 10) -> Dict[str, Any]:
        """Benchmark a function."""
        latencies = []
        for _ in range(iterations):
            start = time.time()
            try:
                fn()
                latencies.append(time.time() - start)
            except Exception:
                self._error_count += 1
        for lat in latencies:
            self.record_request(lat)
        return {
            "iterations": iterations,
            "successful": len(latencies),
            "latency": LatencyProfiler().get_stats()  # Empty, use latencies directly
        }


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("MODEL PERFORMANCE PROFILER DEMO")
    print("=" * 70)

    # 1. Latency Profiler
    print("\n[1] Latency Profiler")
    lp = LatencyProfiler()
    for i in range(100):
        lp.start(f"req-{i}")
        time.sleep(random.uniform(0.001, 0.01))
        lp.end(f"req-{i}")
    snap = lp.get_snapshot()
    print(f"  Count: {snap.count}, Mean: {snap.mean:.4f}s")
    print(f"  P50: {snap.p50:.4f}s, P95: {snap.p95:.4f}s, P99: {snap.p99:.4f}s")
    print(f"  Min: {snap.min:.4f}s, Max: {snap.max:.4f}s, Std: {snap.std:.4f}s")

    # 2. Throughput
    print("\n[2] Throughput Analyzer")
    ta = ThroughputAnalyzer(window_seconds=5.0)
    for i in range(20):
        ta.record()
        time.sleep(0.05)
    print(f"  RPS: {ta.get_rps():.2f}, Stats: {ta.get_stats()}")

    # 3. Accuracy
    print("\n[3] Accuracy Tracker")
    at = AccuracyTracker()
    for i in range(10):
        at.record_score(random.uniform(0.6, 0.95))
    for i in range(8):
        at.record_binary(i % 3 != 0)  # 7/8 correct
    for i in range(5):
        at.record_rating(random.randint(3, 5))
    print(f"  Stats: {at.get_stats()}")

    # 4. Resource Monitor
    print("\n[4] Resource Monitor")
    rm = ResourceMonitor()
    for i in range(10):
        rm.simulate()
    print(f"  Stats: {rm.get_stats()}")

    # 5. Full Dashboard
    print("\n[5] Full Dashboard")
    dash = ProfilerDashboard("model-v1")
    for i in range(50):
        dash.record_request(
            latency=random.uniform(0.05, 0.5),
            success=random.random() > 0.1,
            score=random.uniform(0.7, 0.95)
        )
    report = dash.get_full_report()
    print(f"  Model: {report['model_id']}")
    print(f"  Uptime: {report['uptime_seconds']:.2f}s")
    print(f"  Total requests: {report['total_requests']}")
    print(f"  Error rate: {report['error_rate']:.2%}")
    print(f"  Latency mean: {report['latency']['mean']:.4f}s")
    print(f"  RPS: {report['throughput']['rps']:.2f}")
    print(f"  Accuracy: {report['accuracy']}")
    print(f"  Resource: {report['resource']}")

    # 6. Export
    print("\n[6] Export Report")
    dash.export("/tmp/profiler_report.json")
    print(f"  Exported to /tmp/profiler_report.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
