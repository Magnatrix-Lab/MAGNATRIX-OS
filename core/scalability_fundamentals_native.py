"""
scalability_fundamentals_native.py
MAGNATRIX-OS — Scalability Fundamentals Engine

Inspired by donnemartin/system-design-primer:
Core scalability primitives: horizontal vs vertical scaling, latency, throughput, 
availability, redundancy, idempotency. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ScalingMetric:
    metric_name: str
    value: float
    unit: str
    timestamp: str = ""
    context: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class ScalabilityFundamentals:
    """Core system scalability fundamentals calculator and analyzer."""

    def __init__(self, data_dir: str = "./scalability"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.metrics: List[ScalingMetric] = []
        self._load()

    def _load(self) -> None:
        file = self.data_dir / "metrics.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.metrics = [ScalingMetric(**m) for m in data]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.data_dir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump([asdict(m) for m in self.metrics], f, indent=2)

    def record_latency(self, ms: float, context: str = "") -> ScalingMetric:
        m = ScalingMetric("latency", ms, "ms", context=context)
        self.metrics.append(m)
        self._save()
        return m

    def record_throughput(self, rps: float, context: str = "") -> ScalingMetric:
        m = ScalingMetric("throughput", rps, "req/s", context=context)
        self.metrics.append(m)
        self._save()
        return m

    def availability(self, uptime_hours: float, total_hours: float) -> float:
        """Calculate availability percentage."""
        if total_hours <= 0:
            return 0.0
        return round((uptime_hours / total_hours) * 100, 4)

    def availability_nines(self, percentage: float) -> int:
        """Convert availability to nines (e.g., 99.99% = 4 nines)."""
        nines = 0
        target = 99.9
        while percentage >= target and nines < 9:
            nines += 1
            target = 100 - (10 ** (-nines))
        return nines

    def downtime_per_year(self, nines: int) -> float:
        """Calculate max downtime per year for n-nines availability."""
        minutes_per_year = 365 * 24 * 60
        return round(minutes_per_year * (10 ** (-nines)), 4)

    def horizontal_scale_capacity(self, servers: int, server_capacity: float) -> float:
        return servers * server_capacity

    def vertical_scale_capacity(self, base_capacity: float, multiplier: float) -> float:
        return base_capacity * multiplier

    def get_stats(self) -> Dict[str, Any]:
        latencies = [m.value for m in self.metrics if m.metric_name == "latency"]
        throughputs = [m.value for m in self.metrics if m.metric_name == "throughput"]
        return {
            "total_metrics": len(self.metrics),
            "avg_latency_ms": round(sum(latencies) / max(1, len(latencies)), 2) if latencies else 0,
            "avg_throughput_rps": round(sum(throughputs) / max(1, len(throughputs)), 2) if throughputs else 0,
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["ScalabilityFundamentals", "ScalingMetric"]