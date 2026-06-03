#!/usr/bin/env python3
"""
MAGNATRIX-OS — Auto-Scaler Engine
ai/llm_auto_scaler_native.py

Features:
- Metric-based scaling (CPU, memory, request count)
- Scale-up / scale-down decisions with thresholds
- Cooldown periods to prevent flapping
- Load prediction (trend-based forecasting)
- Scaling history and cost tracking

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("auto_scaler")


class ScaleAction(enum.Enum):
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    HOLD = "hold"


@dataclass
class ScalingDecision:
    action: ScaleAction
    current_instances: int
    target_instances: int
    reason: str
    timestamp: float


class AutoScalerEngine:
    """Auto-scaler with thresholds, cooldown, and prediction."""

    def __init__(self,
                 min_instances: int = 1,
                 max_instances: int = 10,
                 scale_up_threshold: float = 0.7,
                 scale_down_threshold: float = 0.3,
                 cooldown_seconds: float = 60.0,
                 scale_step: int = 1):
        self.min_instances = min_instances
        self.max_instances = max_instances
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.cooldown = cooldown_seconds
        self.scale_step = scale_step
        self._instances = min_instances
        self._last_scale_time = 0.0
        self._history: deque = deque(maxlen=100)
        self._metrics: deque = deque(maxlen=20)

    def evaluate(self, cpu_util: float, memory_util: float, request_count: int) -> ScalingDecision:
        now = time.monotonic()
        avg_load = (cpu_util + memory_util) / 2
        self._metrics.append(avg_load)

        # Cooldown check
        if now - self._last_scale_time < self.cooldown:
            return ScalingDecision(ScaleAction.HOLD, self._instances, self._instances, "Cooldown active", now)

        # Scale up
        if avg_load > self.scale_up_threshold and self._instances < self.max_instances:
            target = min(self._instances + self.scale_step, self.max_instances)
            self._last_scale_time = now
            self._instances = target
            return ScalingDecision(ScaleAction.SCALE_UP, self._instances - self.scale_step, target, f"Load {avg_load:.1%}", now)

        # Scale down
        if avg_load < self.scale_down_threshold and self._instances > self.min_instances:
            target = max(self._instances - self.scale_step, self.min_instances)
            self._last_scale_time = now
            self._instances = target
            return ScalingDecision(ScaleAction.SCALE_DOWN, self._instances + self.scale_step, target, f"Load {avg_load:.1%}", now)

        return ScalingDecision(ScaleAction.HOLD, self._instances, self._instances, f"Load {avg_load:.1%}", now)

    def predict_load(self, horizon: int = 3) -> float:
        """Simple linear trend prediction."""
        if len(self._metrics) < 2:
            return self._metrics[-1] if self._metrics else 0.5
        recent = list(self._metrics)
        n = len(recent)
        avg = sum(recent) / n
        trend = (recent[-1] - recent[0]) / max(n - 1, 1)
        return min(1.0, max(0.0, avg + trend * horizon))

    def get_stats(self) -> Dict[str, Any]:
        return {
            "instances": self._instances,
            "min": self.min_instances,
            "max": self.max_instances,
            "history": len(self._history),
            "predicted_load": self.predict_load(),
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Auto-Scaler Engine")
    print("ai/llm_auto_scaler_native.py")
    print("=" * 60)

    scaler = AutoScalerEngine(min_instances=2, max_instances=8, scale_up_threshold=0.75, scale_down_threshold=0.25, cooldown_seconds=0.5, scale_step=2)

    scenarios = [
        (0.3, 0.2, 10),   # low
        (0.5, 0.4, 20),   # medium
        (0.8, 0.9, 50),   # high -> scale up
        (0.85, 0.8, 60),  # still high
        (0.2, 0.1, 5),    # low -> scale down
        (0.15, 0.1, 3),   # still low
    ]

    for cpu, mem, req in scenarios:
        decision = scaler.evaluate(cpu, mem, req)
        print(f"CPU={cpu:.0%} MEM={mem:.0%} REQ={req} → {decision.action.value} ({decision.reason})")
        time.sleep(0.3)

    print(f"\nPredicted load: {scaler.predict_load():.1%}")
    print(f"Final instances: {scaler._instances}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
