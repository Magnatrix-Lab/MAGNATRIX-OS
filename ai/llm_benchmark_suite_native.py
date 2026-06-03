"""LLM Benchmark Suite — Native Python (stdlib only)."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class BenchmarkMetric(Enum):
    LATENCY = auto()
    THROUGHPUT = auto()
    ACCURACY = auto()
    MEMORY = auto()
    CPU = auto()

@dataclass
class BenchmarkCase:
    id: str
    name: str
    setup_fn: Optional[Callable[[], Any]] = None
    run_fn: Callable[[Any], Any] = None
    metric: BenchmarkMetric = BenchmarkMetric.LATENCY
    iterations: int = 10
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BenchmarkResult:
    case_id: str
    metric: BenchmarkMetric
    values: List[float]
    avg: float
    min: float
    max: float
    std: float

class BenchmarkSuite:
    def __init__(self) -> None:
        self._cases: Dict[str, BenchmarkCase] = {}

    def add_case(self, case: BenchmarkCase) -> None:
        self._cases[case.id] = case

    def run(self, case_id: str) -> BenchmarkResult:
        case = self._cases.get(case_id)
        if not case:
            raise ValueError("Case not found: " + case_id)
        state = case.setup_fn() if case.setup_fn else None
        values = []
        for _ in range(case.iterations):
            start = time.time()
            case.run_fn(state)
            values.append(time.time() - start)
        avg = sum(values) / len(values)
        min_v = min(values)
        max_v = max(values)
        variance = sum((v - avg) ** 2 for v in values) / len(values)
        std = variance ** 0.5
        return BenchmarkResult(case_id, case.metric, values, avg, min_v, max_v, std)

    def run_all(self) -> List[BenchmarkResult]:
        return [self.run(cid) for cid in self._cases]

    def compare(self, result1: BenchmarkResult, result2: BenchmarkResult) -> float:
        if result1.avg == 0:
            return float('inf')
        return (result2.avg - result1.avg) / result1.avg * 100.0

    def get_stats(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        return {"cases": len(results), "total_iterations": sum(len(r.values) for r in results), "avg_latency": sum(r.avg for r in results if r.metric == BenchmarkMetric.LATENCY) / max(1, sum(1 for r in results if r.metric == BenchmarkMetric.LATENCY))}

def run() -> None:
    print("Benchmark Suite test")
    e = BenchmarkSuite()
    e.add_case(BenchmarkCase("b1", "list_append", lambda: [], lambda s: s.append(1), BenchmarkMetric.LATENCY, 100))
    e.add_case(BenchmarkCase("b2", "dict_lookup", lambda: {"a": 1}, lambda s: s.get("a"), BenchmarkMetric.LATENCY, 100))
    results = e.run_all()
    for r in results:
        print("  " + r.case_id + ": avg=" + str(r.avg) + "s, min=" + str(r.min) + "s, max=" + str(r.max) + "s")
    print("  Stats: " + str(e.get_stats(results)))
    print("Benchmark Suite test complete.")

if __name__ == "__main__":
    run()
