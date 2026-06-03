#!/usr/bin/env python3
"""
MAGNATRIX-OS — A/B Testing Engine
ai/llm_a_b_testing_native.py

Features:
- Variant assignment (random, weighted, user-hash based)
- Experiment configuration (control, treatment, duration, sample size)
- Metric tracking (conversion, engagement, accuracy per variant)
- Statistical significance testing (simulated z-test)
- Winner selection and rollout

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import hashlib
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ab_testing")


class AssignmentStrategy(enum.Enum):
    RANDOM = "random"
    WEIGHTED = "weighted"
    HASH = "hash"


@dataclass
class Variant:
    id: str
    name: str
    weight: float = 1.0
    metrics: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))

    def add_metric(self, metric: str, value: float) -> None:
        self.metrics[metric].append(value)

    def avg(self, metric: str) -> float:
        vals = self.metrics.get(metric, [])
        return sum(vals) / len(vals) if vals else 0.0


@dataclass
class Experiment:
    id: str
    name: str
    variants: List[Variant]
    control_id: str
    strategy: AssignmentStrategy = AssignmentStrategy.RANDOM
    min_sample_size: int = 100
    started_at: float = 0.0

    def __post_init__(self):
        if self.started_at == 0.0:
            self.started_at = time.monotonic()


class ABTestingEngine:
    """A/B testing with variant assignment and statistical analysis."""

    def __init__(self):
        self._experiments: Dict[str, Experiment] = {}
        self._user_assignments: Dict[str, Dict[str, str]] = {}  # user -> {exp_id: variant_id}

    def create_experiment(self, experiment: Experiment) -> None:
        self._experiments[experiment.id] = experiment

    def assign(self, user_id: str, experiment_id: str) -> Optional[Variant]:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return None
        # Check if already assigned
        if user_id in self._user_assignments and experiment_id in self._user_assignments[user_id]:
            vid = self._user_assignments[user_id][experiment_id]
            return next((v for v in exp.variants if v.id == vid), None)
        # Assign new
        if exp.strategy == AssignmentStrategy.HASH:
            h = hashlib.md5(f"{user_id}:{experiment_id}".encode()).hexdigest()
            idx = int(h, 16) % len(exp.variants)
            variant = exp.variants[idx]
        elif exp.strategy == AssignmentStrategy.WEIGHTED:
            total = sum(v.weight for v in exp.variants)
            r = random.uniform(0, total)
            cum = 0.0
            variant = None
            for v in exp.variants:
                cum += v.weight
                if r <= cum:
                    variant = v
                    break
            if not variant:
                variant = exp.variants[-1]
        else:
            variant = random.choice(exp.variants)
        if user_id not in self._user_assignments:
            self._user_assignments[user_id] = {}
        self._user_assignments[user_id][experiment_id] = variant.id
        return variant

    def record(self, experiment_id: str, variant_id: str, metric: str, value: float) -> None:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return
        variant = next((v for v in exp.variants if v.id == variant_id), None)
        if variant:
            variant.add_metric(metric, value)

    def analyze(self, experiment_id: str, metric: str) -> Dict[str, Any]:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return {"error": "Experiment not found"}
        results = {}
        control = next((v for v in exp.variants if v.id == exp.control_id), None)
        control_avg = control.avg(metric) if control else 0.0
        for v in exp.variants:
            avg = v.avg(metric)
            lift = ((avg - control_avg) / max(control_avg, 1e-6)) * 100 if control else 0.0
            n = len(v.metrics.get(metric, []))
            # Simulated significance (p < 0.05 if lift > 5% and n > 100)
            significant = n >= exp.min_sample_size and abs(lift) > 5.0
            results[v.id] = {
                "avg": avg,
                "count": n,
                "lift_vs_control": f"{lift:+.1f}%",
                "significant": significant,
            }
        winner = max(results.keys(), key=lambda k: results[k]["avg"]) if results else None
        return {
            "experiment": experiment_id,
            "metric": metric,
            "control": exp.control_id,
            "results": results,
            "winner": winner,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "experiments": len(self._experiments),
            "users_assigned": len(self._user_assignments),
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — A/B Testing Engine")
    print("ai/llm_a_b_testing_native.py")
    print("=" * 60)

    engine = ABTestingEngine()

    # 1. Create experiment
    print("\n[1] Create Experiment")
    exp = Experiment(
        "exp-1", "Prompt Strategy Test",
        [Variant("control", "Standard Prompt", weight=0.5), Variant("treatment", "Chain-of-Thought", weight=0.5)],
        control_id="control",
        strategy=AssignmentStrategy.HASH,
        min_sample_size=50,
    )
    engine.create_experiment(exp)
    print(f"  Created: {exp.name}")

    # 2. Assign users
    print("\n[2] Assign Users")
    users = [f"user-{i}" for i in range(20)]
    assignments = {}
    for u in users:
        v = engine.assign(u, "exp-1")
        assignments[u] = v.id
    print(f"  Assigned {len(users)} users")

    # 3. Record metrics
    print("\n[3] Record Metrics")
    random.seed(42)
    for u in users:
        vid = assignments[u]
        if vid == "control":
            score = random.gauss(0.72, 0.05)
        else:
            score = random.gauss(0.78, 0.05)
        engine.record("exp-1", vid, "accuracy", score)
    print(f"  Recorded {len(users)} scores")

    # 4. Analyze
    print("\n[4] Analyze Results")
    analysis = engine.analyze("exp-1", "accuracy")
    print(f"  Experiment: {analysis['experiment']}")
    for vid, res in analysis["results"].items():
        print(f"    {vid}: avg={res['avg']:.3f}, count={res['count']}, lift={res['lift_vs_control']}, significant={res['significant']}")
    print(f"  Winner: {analysis['winner']}")

    # 5. Stats
    print("\n[5] Engine Stats")
    print(f"  {engine.get_stats()}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
