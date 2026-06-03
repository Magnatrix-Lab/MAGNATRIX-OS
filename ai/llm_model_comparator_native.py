"""LLM Model Comparator — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class ComparisonMetric(Enum):
    ACCURACY = auto()
    SPEED = auto()
    MEMORY = auto()
    COST = auto()
    QUALITY = auto()

@dataclass
class ModelResult:
    model_id: str
    metric: ComparisonMetric
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)

class ModelComparator:
    def __init__(self) -> None:
        self._results: List[ModelResult] = []

    def add_result(self, result: ModelResult) -> None:
        self._results.append(result)

    def compare(self, metric: ComparisonMetric, higher_is_better: bool = True) -> List[tuple]:
        results = [r for r in self._results if r.metric == metric]
        sorted_results = sorted(results, key=lambda r: r.value, reverse=higher_is_better)
        return [(r.model_id, r.value) for r in sorted_results]

    def get_best(self, metric: ComparisonMetric, higher_is_better: bool = True) -> Optional[str]:
        ranked = self.compare(metric, higher_is_better)
        return ranked[0][0] if ranked else None

    def get_model_scores(self, model_id: str) -> Dict[str, float]:
        return {r.metric.name: r.value for r in self._results if r.model_id == model_id}

    def get_stats(self) -> Dict[str, Any]:
        models = set(r.model_id for r in self._results)
        metrics = set(r.metric.name for r in self._results)
        return {"models": len(models), "metrics": len(metrics), "total_results": len(self._results)}

def run() -> None:
    print("Model Comparator test")
    e = ModelComparator()
    e.add_result(ModelResult("m1", ComparisonMetric.ACCURACY, 0.85))
    e.add_result(ModelResult("m2", ComparisonMetric.ACCURACY, 0.92))
    e.add_result(ModelResult("m3", ComparisonMetric.ACCURACY, 0.78))
    e.add_result(ModelResult("m1", ComparisonMetric.SPEED, 120.0))
    e.add_result(ModelResult("m2", ComparisonMetric.SPEED, 95.0))
    e.add_result(ModelResult("m3", ComparisonMetric.SPEED, 150.0))
    print("  Accuracy ranking: " + str(e.compare(ComparisonMetric.ACCURACY)))
    print("  Speed ranking: " + str(e.compare(ComparisonMetric.SPEED)))
    print("  Best accuracy: " + str(e.get_best(ComparisonMetric.ACCURACY)))
    print("  Stats: " + str(e.get_stats()))
    print("Model Comparator test complete.")

if __name__ == "__main__":
    run()
