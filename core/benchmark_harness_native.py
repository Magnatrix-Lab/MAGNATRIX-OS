
"""
benchmark_harness_native.py
MAGNATRIX-OS — Benchmark Harness

Inspired by A-Evolve benchmark adapters: MCP-Atlas, SWE-bench,
Terminal-Bench, SkillsBench, ARC-AGI, OSWorld, τ-bench, WebArena.

Universal benchmark adapter framework with zero manual harness engineering.
Pure Python standard library.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum, auto
from datetime import datetime


class BenchmarkType(Enum):
    MCP_ATLAS = "mcp-atlas"
    SWE_BENCH = "swe-bench"
    TERMINAL_BENCH = "terminal-bench"
    SKILLS_BENCH = "skills-bench"
    ARC_AGI = "arc-agi"
    OSWORLD = "osworld"
    TAU_BENCH = "tau-bench"
    WEBARENA = "webarena"
    CL_BENCH = "cl-bench"
    CUSTOM = "custom"


@dataclass
class BenchmarkResult:
    benchmark: str
    score: float
    total_tasks: int
    passed_tasks: int
    failed_tasks: int
    latency_ms: float
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BenchmarkHarness:
    """Universal benchmark adapter for evaluating evolved agents."""

    def __init__(self, output_dir: str = "./benchmark_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.adapters: Dict[str, Callable] = {}
        self.results: List[BenchmarkResult] = []
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register_adapter(BenchmarkType.MCP_ATLAS.value, self._default_adapter)
        self.register_adapter(BenchmarkType.SWE_BENCH.value, self._default_adapter)
        self.register_adapter(BenchmarkType.TERMINAL_BENCH.value, self._default_adapter)
        self.register_adapter(BenchmarkType.SKILLS_BENCH.value, self._default_adapter)
        self.register_adapter(BenchmarkType.ARC_AGI.value, self._default_adapter)
        self.register_adapter(BenchmarkType.OSWORLD.value, self._default_adapter)
        self.register_adapter(BenchmarkType.TAU_BENCH.value, self._default_adapter)
        self.register_adapter(BenchmarkType.WEBARENA.value, self._default_adapter)
        self.register_adapter(BenchmarkType.CL_BENCH.value, self._default_adapter)

    def register_adapter(self, benchmark_name: str, adapter_fn: Callable) -> None:
        self.adapters[benchmark_name] = adapter_fn

    def run(self, benchmark: str, agent: Any, tasks: Optional[List[Dict]] = None) -> BenchmarkResult:
        adapter = self.adapters.get(benchmark, self._default_adapter)
        start = time.time()
        try:
            score, passed, failed = adapter(agent, tasks or [])
        except Exception as e:
            score, passed, failed = 0.0, 0, 0
        latency = (time.time() - start) * 1000
        total = len(tasks) if tasks else 0
        total = max(total, passed + failed)
        result = BenchmarkResult(
            benchmark=benchmark,
            score=score,
            total_tasks=total,
            passed_tasks=passed,
            failed_tasks=failed,
            latency_ms=latency,
        )
        self.results.append(result)
        self._save_result(result)
        return result

    def run_suite(self, benchmarks: List[str], agent: Any, tasks_map: Optional[Dict[str, List[Dict]]] = None) -> Dict[str, BenchmarkResult]:
        tasks_map = tasks_map or {}
        return {b: self.run(b, agent, tasks_map.get(b, [])) for b in benchmarks}

    def _default_adapter(self, agent: Any, tasks: List[Dict]) -> Tuple[float, int, int]:
        """Default adapter: simulate benchmark scoring."""
        if not tasks:
            return 0.5, 0, 0
        passed = 0
        for task in tasks:
            # Simulated evaluation: check if agent has relevant skill
            if hasattr(agent, "skills") and task.get("required_skill") in agent.skills:
                passed += 1
        total = len(tasks)
        score = passed / total if total > 0 else 0.0
        return score, passed, total - passed

    def _save_result(self, result: BenchmarkResult) -> None:
        filename = f"{result.benchmark}_{int(time.time())}.json"
        path = self.output_dir / filename
        with open(path, "w") as f:
            json.dump(asdict(result), f, indent=2)

    def get_leaderboard(self) -> List[Dict]:
        """Aggregate results by benchmark."""
        best: Dict[str, BenchmarkResult] = {}
        for r in self.results:
            if r.benchmark not in best or r.score > best[r.benchmark].score:
                best[r.benchmark] = r
        return [asdict(r) for r in sorted(best.values(), key=lambda x: x.score, reverse=True)]

    def compare(self, baseline: BenchmarkResult, evolved: BenchmarkResult) -> Dict:
        """Compare baseline vs evolved results."""
        delta = evolved.score - baseline.score
        pp_uplift = delta * 100
        return {
            "benchmark": baseline.benchmark,
            "baseline_score": baseline.score,
            "evolved_score": evolved.score,
            "delta": delta,
            "percentage_points_uplift": pp_uplift,
            "improved": delta > 0,
        }

    def to_dict(self) -> Dict:
        return {
            "registered_adapters": list(self.adapters.keys()),
            "total_results": len(self.results),
            "leaderboard": self.get_leaderboard(),
        }


__all__ = ["BenchmarkHarness", "BenchmarkResult", "BenchmarkType"]
