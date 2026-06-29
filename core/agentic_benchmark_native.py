"""
agentic_benchmark_native.py
MAGNATRIX-OS — Agentic Benchmark

Inspired by Ponytail benchmarks: Measure agentic LOC, safety, and efficiency. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class BenchmarkResult:
    result_id: str
    benchmark_name: str
    agent_id: str
    loc_generated: int
    loc_saved: int
    safety_score: float
    efficiency_score: float
    passed: bool
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class AgenticBenchmark:
    """Measure agentic code generation: LOC, safety, efficiency."""

    BENCHMARKS = ["loc_efficiency", "safety_guard", "reuse_rate", "yagni_compliance", "comprehension_coverage"]

    def __init__(self, cache_dir: str = "./agentic_benchmarks"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.results: Dict[str, BenchmarkResult] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "results.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for rid, rd in data.items():
                        self.results[rid] = BenchmarkResult(**rd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump({rid: asdict(r) for rid, r in self.results.items()}, f, indent=2)

    def run(self, result_id: str, benchmark_name: str, agent_id: str,
            loc_generated: int, loc_saved: int, errors: int = 0, warnings: int = 0,
            yagni_rejects: int = 0, comprehension_checks: int = 0) -> BenchmarkResult:
        """Run a benchmark and record results."""
        safety = max(0.0, 1.0 - errors * 0.1 - warnings * 0.05)
        efficiency = max(0.0, min(1.0, loc_saved / max(1, loc_generated) + yagni_rejects * 0.05))
        passed = safety >= 0.7 and efficiency >= 0.5
        result = BenchmarkResult(
            result_id=result_id, benchmark_name=benchmark_name, agent_id=agent_id,
            loc_generated=loc_generated, loc_saved=loc_saved, safety_score=round(safety, 2),
            efficiency_score=round(efficiency, 2), passed=passed,
        )
        self.results[result_id] = result
        self._save()
        return result

    def get_leaderboard(self, benchmark_name: Optional[str] = None) -> List[BenchmarkResult]:
        results = [r for r in self.results.values() if not benchmark_name or r.benchmark_name == benchmark_name]
        return sorted(results, key=lambda x: x.efficiency_score + x.safety_score, reverse=True)[:10]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r.passed)
        avg_safety = sum(r.safety_score for r in self.results.values()) / max(1, total)
        avg_efficiency = sum(r.efficiency_score for r in self.results.values()) / max(1, total)
        return {
            "total_runs": total, "passed": passed, "failed": total - passed,
            "avg_safety": round(avg_safety, 2), "avg_efficiency": round(avg_efficiency, 2),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["AgenticBenchmark", "BenchmarkResult"]