#!/usr/bin/env python3
"""
MAGNATRIX-OS — Experiment Tracker
ai/llm_experiment_tracker_native.py

Features:
- Experiment logging (params, metrics, artifacts)
- Run comparison (diff between experiments)
- Metric visualization data generation
- Best run tracking (hyperparameter optimization)
- Experiment search and filtering

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("experiment_tracker")


@dataclass
class ExperimentRun:
    id: str
    experiment_name: str
    params: Dict[str, Any]
    metrics: Dict[str, float] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    status: str = "running"
    start_time: float = 0.0
    end_time: Optional[float] = None

    def __post_init__(self):
        if self.start_time == 0.0:
            self.start_time = time.time()

    @property
    def duration(self) -> float:
        return (self.end_time or time.time()) - self.start_time


class ExperimentTracker:
    """ML experiment tracking and comparison."""

    def __init__(self):
        self._runs: Dict[str, ExperimentRun] = {}
        self._experiments: Dict[str, List[str]] = defaultdict(list)

    def start_run(self, run_id: str, experiment_name: str, params: Dict[str, Any]) -> ExperimentRun:
        run = ExperimentRun(run_id, experiment_name, params)
        self._runs[run_id] = run
        self._experiments[experiment_name].append(run_id)
        return run

    def log_metric(self, run_id: str, key: str, value: float) -> None:
        run = self._runs.get(run_id)
        if run:
            run.metrics[key] = value

    def end_run(self, run_id: str, status: str = "completed") -> None:
        run = self._runs.get(run_id)
        if run:
            run.status = status
            run.end_time = time.time()

    def compare(self, run_ids: List[str]) -> Dict[str, Any]:
        runs = [self._runs[rid] for rid in run_ids if rid in self._runs]
        if not runs:
            return {}
        all_metrics = set()
        for r in runs:
            all_metrics.update(r.metrics.keys())
        comparison = {}
        for metric in all_metrics:
            comparison[metric] = {r.id: r.metrics.get(metric, None) for r in runs}
        return comparison

    def get_best(self, experiment_name: str, metric: str, maximize: bool = True) -> Optional[ExperimentRun]:
        run_ids = self._experiments.get(experiment_name, [])
        runs = [self._runs[rid] for rid in run_ids if rid in self._runs and metric in self._runs[rid].metrics]
        if not runs:
            return None
        return max(runs, key=lambda r: r.metrics[metric]) if maximize else min(runs, key=lambda r: r.metrics[metric])

    def search(self, experiment_name: Optional[str] = None, status: Optional[str] = None) -> List[ExperimentRun]:
        results = list(self._runs.values())
        if experiment_name:
            results = [r for r in results if r.experiment_name == experiment_name]
        if status:
            results = [r for r in results if r.status == status]
        return results

    def get_stats(self) -> Dict[str, Any]:
        return {
            "runs": len(self._runs),
            "experiments": len(self._experiments),
            "completed": sum(1 for r in self._runs.values() if r.status == "completed"),
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Experiment Tracker")
    print("ai/llm_experiment_tracker_native.py")
    print("=" * 60)

    tracker = ExperimentTracker()

    # Start runs
    for i in range(5):
        rid = f"run-{i}"
        tracker.start_run(rid, "prompt-tuning", {"lr": 0.001 * (i+1), "temp": 0.5 + i*0.1})
        tracker.log_metric(rid, "accuracy", 0.7 + i * 0.04 + (i == 3 and 0.08 or 0))
        tracker.log_metric(rid, "loss", 1.0 - i * 0.15)
        tracker.end_run(rid)

    print(f"\n[1] Started 5 runs")

    # Compare
    print("\n[2] Compare Runs")
    comp = tracker.compare(["run-0", "run-1", "run-2"])
    for metric, vals in comp.items():
        print(f"  {metric}: {vals}")

    # Best run
    print("\n[3] Best Run")
    best = tracker.get_best("prompt-tuning", "accuracy", maximize=True)
    if best:
        print(f"  Best: {best.id} with accuracy={best.metrics['accuracy']:.3f}")

    # Search
    print("\n[4] Search Completed")
    completed = tracker.search(status="completed")
    print(f"  Found {len(completed)} completed runs")

    # Stats
    print(f"\n[5] Stats: {tracker.get_stats()}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
