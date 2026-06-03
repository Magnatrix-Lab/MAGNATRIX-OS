#!/usr/bin/env python3
"""
MAGNATRIX-OS — Resource Monitor Engine
ai/llm_resource_monitor_native.py

Features:
- CPU/Memory/Disk usage tracking
- Resource threshold alerts
- Resource prediction (trend-based)
- Bottleneck identification
- Resource allocation recommendations

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("resource_monitor")


@dataclass
class ResourceSnapshot:
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_mbps: float
    timestamp: float


class ResourceMonitorEngine:
    """System resource monitoring and prediction."""

    def __init__(self, history_size: int = 100):
        self._history: deque = deque(maxlen=history_size)
        self._alerts: List[Dict[str, Any]] = []

    def record(self, snapshot: ResourceSnapshot) -> None:
        self._history.append(snapshot)
        self._check_alerts(snapshot)

    def _check_alerts(self, snap: ResourceSnapshot) -> None:
        if snap.cpu_percent > 80:
            self._alerts.append({"type": "cpu", "severity": "high", "value": snap.cpu_percent, "time": snap.timestamp})
        if snap.memory_percent > 85:
            self._alerts.append({"type": "memory", "severity": "high", "value": snap.memory_percent, "time": snap.timestamp})
        if snap.disk_percent > 90:
            self._alerts.append({"type": "disk", "severity": "critical", "value": snap.disk_percent, "time": snap.timestamp})

    def predict(self, resource: str = "cpu", horizon: int = 5) -> float:
        if len(self._history) < 2:
            return 50.0
        values = [getattr(s, resource) for s in self._history]
        trend = (values[-1] - values[0]) / max(len(values) - 1, 1)
        return min(100, max(0, values[-1] + trend * horizon))

    def bottleneck(self) -> Optional[str]:
        if not self._history:
            return None
        latest = self._history[-1]
        max_val = max(latest.cpu_percent, latest.memory_percent, latest.disk_percent)
        if max_val == latest.cpu_percent:
            return "cpu"
        if max_val == latest.memory_percent:
            return "memory"
        return "disk"

    def recommend(self) -> List[str]:
        if not self._history:
            return []
        latest = self._history[-1]
        recs = []
        if latest.cpu_percent > 70:
            recs.append("Consider scaling up CPU or optimizing compute")
        if latest.memory_percent > 75:
            recs.append("Consider increasing memory or reducing cache size")
        if latest.disk_percent > 80:
            recs.append("Consider disk cleanup or expansion")
        return recs

    def get_stats(self) -> Dict[str, Any]:
        if not self._history:
            return {}
        latest = self._history[-1]
        return {
            "latest": {"cpu": latest.cpu_percent, "memory": latest.memory_percent, "disk": latest.disk_percent},
            "alerts": len(self._alerts),
            "bottleneck": self.bottleneck(),
            "recommendations": self.recommend(),
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Resource Monitor Engine")
    print("ai/llm_resource_monitor_native.py")
    print("=" * 60)

    engine = ResourceMonitorEngine()

    for i in range(10):
        snap = ResourceSnapshot(
            cpu_percent=40 + i * 5 + random.gauss(0, 3),
            memory_percent=50 + i * 3 + random.gauss(0, 2),
            disk_percent=60 + i * 1 + random.gauss(0, 1),
            network_mbps=100 + random.gauss(0, 10),
            timestamp=time.time(),
        )
        engine.record(snap)

    print(f"\n[1] Stats: {engine.get_stats()}")
    print(f"[2] CPU prediction (5 steps): {engine.predict('cpu_percent', 5):.1f}%")
    print(f"[3] Bottleneck: {engine.bottleneck()}")
    print(f"[4] Alerts: {len(engine._alerts)}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
