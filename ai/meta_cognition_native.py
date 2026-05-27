#!/usr/bin/env python3
"""Meta-Cognition Engine — MAGNATRIX-OS ASI Expansion
Path: ai/meta_cognition_native.py
License: AGPL-3.0
Depends: Python 3.11+ stdlib only.
"""

from __future__ import annotations
import json, logging, math, statistics, sys, time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

@dataclass
class PerformanceLog:
    task_id: str; strategy: str; accuracy: float; latency: float; timestamp: float

@dataclass
class Strategy:
    name: str; params: Dict[str, Any]; success_rate: float = 0.0; avg_latency: float = 0.0

class MetaCognition:
    """Performance monitor, strategy selector, confidence calibration."""

    def __init__(self):
        self.logs: List[PerformanceLog] = []
        self.strategies: Dict[str, Strategy] = {}
        self.confidence_history: List[Tuple[float, bool]] = []  # (confidence, correct)

    def register_strategy(self, name: str, params: Dict[str, Any]) -> None:
        self.strategies[name] = Strategy(name, params)

    def record(self, task_id: str, strategy: str, accuracy: float, latency: float) -> None:
        self.logs.append(PerformanceLog(task_id, strategy, accuracy, latency, time.time()))
        self._update_strategy_stats(strategy)

    def _update_strategy_stats(self, strategy_name: str) -> None:
        entries = [l for l in self.logs if l.strategy == strategy_name]
        if not entries: return
        s = self.strategies[strategy_name]
        s.success_rate = statistics.mean(l.accuracy for l in entries)
        s.avg_latency = statistics.mean(l.latency for l in entries)

    def select_strategy(self, task_features: Dict[str, Any]) -> Strategy:
        """Select best strategy based on historical performance."""
        if not self.strategies:
            raise ValueError("No strategies registered")
        # Epsilon-greedy: 10% exploration
        import random
        if random.random() < 0.1:
            return random.choice(list(self.strategies.values()))
        return max(self.strategies.values(), key=lambda s: s.success_rate)

    def calibrate_confidence(self, confidence: float, correct: bool) -> float:
        """Return calibrated confidence using Platt scaling approximation."""
        self.confidence_history.append((confidence, correct))
        if len(self.confidence_history) < 10:
            return confidence
        # Simple calibration: if overconfident, dampen; if underconfident, boost
        bins: Dict[int, List[bool]] = defaultdict(list)
        for conf, corr in self.confidence_history:
            b = min(9, int(conf * 10))
            bins[b].append(corr)
        bin_acc = {b: statistics.mean(v) for b, v in bins.items() if v}
        b = min(9, int(confidence * 10))
        if b in bin_acc:
            return 0.7 * confidence + 0.3 * bin_acc[b]
        return confidence

    def detect_recurrent_failure(self, window: int = 10) -> Optional[str]:
        """Detect if recent tasks show declining performance."""
        if len(self.logs) < window: return None
        recent = self.logs[-window:]
        accs = [l.accuracy for l in recent]
        if statistics.mean(accs) < 0.5:
            return f"Performance degraded: mean accuracy {statistics.mean(accs):.2f}"
        return None

    def get_report(self) -> Dict[str, Any]:
        if not self.logs: return {}
        return {
            "total_tasks": len(self.logs),
            "mean_accuracy": statistics.mean(l.accuracy for l in self.logs),
            "mean_latency": statistics.mean(l.latency for l in self.logs),
            "strategies": {name: {"success_rate": s.success_rate, "avg_latency": s.avg_latency}
                           for name, s in self.strategies.items()},
        }

def _self_test():
    print("=" * 55)
    print("Meta-Cognition Engine — Self Test")
    print("=" * 55)
    mc = MetaCognition()
    mc.register_strategy("fast", {"depth": 1})
    mc.register_strategy("deep", {"depth": 5})
    passed, total = 0, 5

    for i in range(20):
        mc.record(f"t{i}", "fast" if i % 2 == 0 else "deep", 0.6 if i % 2 == 0 else 0.9, 0.1 if i % 2 == 0 else 0.5)

    s = mc.select_strategy({})
    ok = s.name == "deep"
    print(f"  [Test 1] Select best strategy: {s.name} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    cal = mc.calibrate_confidence(0.9, True)
    ok = 0 <= cal <= 1
    print(f"  [Test 2] Calibrated confidence: {cal:.3f} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    for i in range(10):
        mc.record(f"fail{i}", "fast", 0.2, 0.1)
    alert = mc.detect_recurrent_failure()
    ok = alert is not None and "degraded" in alert
    print(f"  [Test 3] Failure detection: {alert is not None} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    report = mc.get_report()
    ok = "total_tasks" in report and report["total_tasks"] == 30
    print(f"  [Test 4] Report: {report['total_tasks']} tasks — {'PASS' if ok else 'FAIL'}")
    passed += ok

    ok = mc.strategies["deep"].success_rate > mc.strategies["fast"].success_rate
    print(f"  [Test 5] Strategy stats correct — {'PASS' if ok else 'FAIL'}")
    passed += ok

    print("=" * 55)
    print(f"PASS: {passed}/{total} tests")
    print("=" * 55)
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    _self_test()
