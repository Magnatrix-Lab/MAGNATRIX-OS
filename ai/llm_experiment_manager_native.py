"""
llm_experiment_manager_native.py
MAGNATRIX-OS Experiment Manager Engine
Native Python, stdlib only.
Provides experiment tracking, parameter sweeps, result comparison, and reproducibility logs.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple


class ExperimentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class ExperimentRun:
    run_id: str
    experiment_id: str
    params: Dict[str, Any]
    metrics: Dict[str, Any] = field(default_factory=dict)
    status: ExperimentStatus = ExperimentStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    artifacts: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id, "experiment_id": self.experiment_id,
            "params": self.params, "metrics": self.metrics, "status": self.status.value,
            "duration_ms": self.duration_ms, "artifacts": self.artifacts, "tags": self.tags,
        }


@dataclass
class Experiment:
    experiment_id: str
    name: str
    description: str
    base_params: Dict[str, Any] = field(default_factory=dict)
    runs: List[ExperimentRun] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id, "name": self.name,
            "description": self.description, "runs": len(self.runs),
            "created_at": self.created_at, "tags": self.tags,
        }


class ExperimentManagerEngine:
    """Experiment tracking with parameter sweeps and comparison."""

    def __init__(self) -> None:
        self._experiments: Dict[str, Experiment] = {}
        self._run_counter = 0

    def create_experiment(self, experiment_id: str, name: str, description: str,
                          base_params: Optional[Dict[str, Any]] = None, tags: Optional[List[str]] = None) -> Experiment:
        exp = Experiment(experiment_id=experiment_id, name=name, description=description,
                         base_params=base_params or {}, tags=tags or [])
        self._experiments[experiment_id] = exp
        return exp

    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        return self._experiments.get(experiment_id)

    def start_run(self, experiment_id: str, params: Optional[Dict[str, Any]] = None,
                  tags: Optional[List[str]] = None) -> Optional[ExperimentRun]:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return None
        self._run_counter += 1
        run_id = f"{experiment_id}_run_{self._run_counter}"
        merged_params = dict(exp.base_params)
        if params:
            merged_params.update(params)
        run = ExperimentRun(run_id=run_id, experiment_id=experiment_id, params=merged_params,
                            tags=tags or [], status=ExperimentStatus.RUNNING, start_time=time.time())
        exp.runs.append(run)
        return run

    def end_run(self, experiment_id: str, run_id: str, metrics: Optional[Dict[str, Any]] = None,
                status: ExperimentStatus = ExperimentStatus.COMPLETED) -> bool:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return False
        for run in exp.runs:
            if run.run_id == run_id:
                run.status = status
                run.end_time = time.time()
                if metrics:
                    run.metrics.update(metrics)
                return True
        return False

    def log_metric(self, experiment_id: str, run_id: str, key: str, value: Any) -> bool:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return False
        for run in exp.runs:
            if run.run_id == run_id:
                run.metrics[key] = value
                return True
        return False

    def log_artifact(self, experiment_id: str, run_id: str, artifact_path: str) -> bool:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return False
        for run in exp.runs:
            if run.run_id == run_id:
                run.artifacts.append(artifact_path)
                return True
        return False

    def compare_runs(self, experiment_id: str, metric_key: str) -> List[Dict[str, Any]]:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return []
        results = []
        for run in exp.runs:
            if metric_key in run.metrics:
                results.append({
                    "run_id": run.run_id, "params": run.params,
                    "metric": run.metrics[metric_key], "duration_ms": run.duration_ms,
                })
        results.sort(key=lambda x: x["metric"], reverse=True)
        return results

    def get_best_run(self, experiment_id: str, metric_key: str, maximize: bool = True) -> Optional[ExperimentRun]:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return None
        valid_runs = [r for r in exp.runs if metric_key in r.metrics]
        if not valid_runs:
            return None
        return max(valid_runs, key=lambda r: r.metrics[metric_key]) if maximize else min(valid_runs, key=lambda r: r.metrics[metric_key])

    def parameter_sweep(self, experiment_id: str, param_grid: Dict[str, List[Any]]) -> List[ExperimentRun]:
        runs = []
        keys = list(param_grid.keys())
        values = [param_grid[k] for k in keys]
        import itertools
        for combo in itertools.product(*values):
            params = dict(zip(keys, combo))
            run = self.start_run(experiment_id, params)
            if run:
                runs.append(run)
        return runs

    def list_experiments(self, tag: Optional[str] = None) -> List[Experiment]:
        exps = list(self._experiments.values())
        if tag:
            exps = [e for e in exps if tag in e.tags]
        return exps

    def get_stats(self) -> Dict[str, Any]:
        total_runs = sum(len(e.runs) for e in self._experiments.values())
        completed = sum(1 for e in self._experiments.values() for r in e.runs if r.status == ExperimentStatus.COMPLETED)
        return {
            "experiments": len(self._experiments), "total_runs": total_runs,
            "completed": completed, "failed": total_runs - completed,
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({k: [r.to_dict() for r in e.runs] for k, e in self._experiments.items()}, f, indent=2, default=str)


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Experiment Manager Engine")
    print("=" * 60)

    engine = ExperimentManagerEngine()

    exp = engine.create_experiment("exp_001", "Temperature Tuning", "Find optimal temperature",
                                   base_params={"model": "gpt-4o"}, tags=["tuning"])

    print("\n--- Parameter sweep ---")
    runs = engine.parameter_sweep("exp_001", {"temperature": [0.1, 0.5, 0.7, 1.0]})
    print(f"  Started {len(runs)} runs")

    print("\n--- Log metrics ---")
    for i, run in enumerate(runs):
        engine.end_run("exp_001", run.run_id, metrics={"perplexity": 10 - i * 1.5, "accuracy": 0.7 + i * 0.05})

    print("\n--- Compare runs ---")
    comparison = engine.compare_runs("exp_001", "accuracy")
    for r in comparison:
        print(f"  {r['run_id']}: accuracy={r['metric']:.3f}")

    print("\n--- Best run ---")
    best = engine.get_best_run("exp_001", "accuracy", maximize=True)
    if best:
        print(f"  Best: {best.run_id} with {best.metrics}")

    print("\n--- Stats ---")
    print(engine.get_stats())

    print("\nExperiment Manager test complete.")


if __name__ == "__main__":
    run()
