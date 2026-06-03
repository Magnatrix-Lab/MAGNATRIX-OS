"""LLM Regression Checker — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class RegressionStatus(Enum):
    STABLE = auto()
    REGRESSED = auto()
    IMPROVED = auto()
    NEW = auto()

@dataclass
class Baseline:
    id: str
    metric_name: str
    expected_value: float
    tolerance: float = 0.05
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RegressionResult:
    baseline_id: str
    actual_value: float
    status: RegressionStatus
    deviation: float
    message: str

class RegressionChecker:
    def __init__(self) -> None:
        self._baselines: Dict[str, Baseline] = {}

    def add_baseline(self, baseline: Baseline) -> None:
        self._baselines[baseline.id] = baseline

    def check(self, baseline_id: str, actual_value: float) -> RegressionResult:
        baseline = self._baselines.get(baseline_id)
        if not baseline:
            return RegressionResult(baseline_id, actual_value, RegressionStatus.NEW, 0.0, "No baseline")
        deviation = abs(actual_value - baseline.expected_value) / abs(baseline.expected_value) if baseline.expected_value != 0 else abs(actual_value)
        if deviation <= baseline.tolerance:
            status = RegressionStatus.STABLE
            message = "Within tolerance"
        elif actual_value > baseline.expected_value:
            status = RegressionStatus.IMPROVED
            message = "Improved by " + str(deviation * 100) + "%"
        else:
            status = RegressionStatus.REGRESSED
            message = "Regressed by " + str(deviation * 100) + "%"
        return RegressionResult(baseline_id, actual_value, status, deviation, message)

    def check_all(self, results: Dict[str, float]) -> List[RegressionResult]:
        return [self.check(bid, actual) for bid, actual in results.items()]

    def get_regressions(self, results: List[RegressionResult]) -> List[RegressionResult]:
        return [r for r in results if r.status == RegressionStatus.REGRESSED]

    def get_stats(self, results: List[RegressionResult]) -> Dict[str, Any]:
        counts = {}
        for r in results:
            counts[r.status.name] = counts.get(r.status.name, 0) + 1
        return {"total": len(results), "by_status": counts, "regressions": len(self.get_regressions(results))}

def run() -> None:
    print("Regression Checker test")
    e = RegressionChecker()
    e.add_baseline(Baseline("b1", "accuracy", 0.95, 0.02))
    e.add_baseline(Baseline("b2", "latency", 0.1, 0.1))
    e.add_baseline(Baseline("b3", "memory", 1024, 0.05))
    results = e.check_all({"b1": 0.94, "b2": 0.08, "b3": 1100})
    for r in results:
        print("  " + r.baseline_id + ": " + r.status.name + " - " + r.message)
    print("  Stats: " + str(e.get_stats(results)))
    print("Regression Checker test complete.")

if __name__ == "__main__":
    run()
