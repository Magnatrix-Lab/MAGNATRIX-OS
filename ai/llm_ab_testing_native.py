"""A/B Testing Framework — Experiment design, traffic splitting, statistical analysis, rollout.

Modul ini menyediakan:
- Experiment designer dengan variant generation
- TrafficSplitter untuk weighted/random traffic allocation
- StatisticalAnalyzer untuk significance testing, confidence intervals
- RolloutManager untuk staged rollout dan kill switches
- ResultTracker untuk experiment metrics dan reporting
"""

from __future__ import annotations

import json
import time
import uuid
import random
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class ExperimentStatus(Enum):
    DRAFT = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    CANCELLED = auto()


class VariantType(Enum):
    CONTROL = "control"
    TREATMENT = "treatment"
    BASELINE = "baseline"


class RolloutStage(Enum):
    CANARY = 0.05
    P10 = 0.10
    P25 = 0.25
    P50 = 0.50
    P75 = 0.75
    FULL = 1.00


@dataclass
class Variant:
    """Single experiment variant."""
    variant_id: str
    name: str
    variant_type: VariantType
    weight: float = 0.5  # traffic allocation weight
    config: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, List[float]] = field(default_factory=dict)

    def record(self, metric_name: str, value: float) -> None:
        self.metrics.setdefault(metric_name, []).append(value)

    def mean(self, metric_name: str) -> float:
        vals = self.metrics.get(metric_name, [])
        return sum(vals) / max(len(vals), 1)

    def count(self, metric_name: str) -> int:
        return len(self.metrics.get(metric_name, []))


@dataclass
class Experiment:
    """A/B experiment definition."""
    experiment_id: str
    name: str
    description: str = ""
    hypothesis: str = ""
    status: ExperimentStatus = ExperimentStatus.DRAFT
    variants: List[Variant] = field(default_factory=list)
    metrics: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    primary_metric: str = "conversion"
    min_sample_size: int = 100
    significance_level: float = 0.05

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "status": self.status.name,
            "variants": len(self.variants),
            "primary_metric": self.primary_metric,
            "min_sample_size": self.min_sample_size,
        }


@dataclass
class ExperimentResult:
    """Final experiment result with statistical analysis."""
    experiment_id: str
    winner: Optional[str] = None
    winner_variant_type: Optional[str] = None
    p_value: float = 1.0
    significant: bool = False
    uplift: float = 0.0
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    sample_sizes: Dict[str, int] = field(default_factory=dict)
    metric_means: Dict[str, Dict[str, float]] = field(default_factory=dict)
    duration: float = 0.0


class TrafficSplitter:
    """Allocate traffic to variants based on weights."""

    def __init__(self, salt: str = ""):
        self.salt = salt
        self._assignments: Dict[str, str] = {}  # user_id -> variant_id

    def assign(self, user_id: str, variants: List[Variant]) -> Variant:
        if user_id in self._assignments:
            vid = self._assignments[user_id]
            for v in variants:
                if v.variant_id == vid:
                    return v
        total = sum(v.weight for v in variants)
        r = random.random() * total
        cum = 0.0
        for v in variants:
            cum += v.weight
            if r <= cum:
                self._assignments[user_id] = v.variant_id
                return v
        return variants[-1]

    def deterministic_assign(self, user_id: str, variants: List[Variant]) -> Variant:
        """Consistent assignment based on user_id hash."""
        h = hash(f"{self.salt}:{user_id}") % 10000
        total = sum(v.weight for v in variants)
        r = (abs(h) / 10000.0) * total
        cum = 0.0
        for v in variants:
            cum += v.weight
            if r <= cum:
                return v
        return variants[-1]

    def get_distribution(self, user_ids: List[str], variants: List[Variant]) -> Dict[str, int]:
        counts = {v.variant_id: 0 for v in variants}
        for uid in user_ids:
            v = self.assign(uid, variants)
            counts[v.variant_id] += 1
        return counts


class StatisticalAnalyzer:
    """Statistical tests for A/B experiments."""

    @staticmethod
    def mean(values: List[float]) -> float:
        return sum(values) / max(len(values), 1)

    @staticmethod
    def variance(values: List[float]) -> float:
        m = StatisticalAnalyzer.mean(values)
        return sum((x - m) ** 2 for x in values) / max(len(values), 1)

    @staticmethod
    def std(values: List[float]) -> float:
        return math.sqrt(StatisticalAnalyzer.variance(values))

    @staticmethod
    def t_test(a: List[float], b: List[float]) -> Tuple[float, float]:
        """Welch's t-test. Returns (t_statistic, p_value_approx)."""
        m1, m2 = StatisticalAnalyzer.mean(a), StatisticalAnalyzer.mean(b)
        s1, s2 = StatisticalAnalyzer.std(a), StatisticalAnalyzer.std(b)
        n1, n2 = len(a), len(b)
        if n1 < 2 or n2 < 2:
            return 0.0, 1.0
        se = math.sqrt((s1**2 / n1) + (s2**2 / n2))
        if se == 0:
            return 0.0, 1.0
        t = (m1 - m2) / se
        # Approximate p-value using normal approximation (simplified)
        p = 2 * (1 - StatisticalAnalyzer._normal_cdf(abs(t)))
        return t, p

    @staticmethod
    def _normal_cdf(x: float) -> float:
        # Abramowitz and Stegun approximation
        b1 = 0.319381530
        b2 = -0.356563782
        b3 = 1.781477937
        b4 = -1.821255978
        b5 = 1.330274429
        p = 0.2316419
        c = 0.39894228
        if x >= 0.0:
            t = 1.0 / (1.0 + p * x)
            return 1.0 - c * math.exp(-x * x / 2.0) * t * (t * (t * (t * (t * b5 + b4) + b3) + b2) + b1)
        else:
            return 1.0 - StatisticalAnalyzer._normal_cdf(-x)

    @staticmethod
    def confidence_interval(values: List[float], level: float = 0.95) -> Tuple[float, float]:
        m = StatisticalAnalyzer.mean(values)
        s = StatisticalAnalyzer.std(values)
        n = len(values)
        if n < 2:
            return (m, m)
        z = 1.96 if level >= 0.95 else 1.645  # simplified z
        margin = z * (s / math.sqrt(n))
        return (m - margin, m + margin)

    @staticmethod
    def required_sample_size(baseline_rate: float, mde: float, power: float = 0.8, alpha: float = 0.05) -> int:
        """Simplified sample size per group."""
        p = baseline_rate
        z_alpha = 1.96
        z_beta = 0.84 if power >= 0.8 else 1.28
        se = math.sqrt(2 * p * (1 - p))
        delta = abs(mde)
        if delta == 0 or se == 0:
            return 1000
        n = ((z_alpha + z_beta) ** 2 * 2 * p * (1 - p)) / (delta ** 2)
        return int(math.ceil(n))

    @staticmethod
    def analyze_experiment(exp: Experiment) -> ExperimentResult:
        control = None
        treatment = None
        for v in exp.variants:
            if v.variant_type == VariantType.CONTROL:
                control = v
            elif v.variant_type == VariantType.TREATMENT:
                treatment = v
        if not control or not treatment:
            return ExperimentResult(experiment_id=exp.experiment_id, winner=None, p_value=1.0)

        a = control.metrics.get(exp.primary_metric, [])
        b = treatment.metrics.get(exp.primary_metric, [])
        t, p = StatisticalAnalyzer.t_test(a, b)
        sig = p < exp.significance_level
        uplift = (StatisticalAnalyzer.mean(b) - StatisticalAnalyzer.mean(a)) / max(abs(StatisticalAnalyzer.mean(a)), 1e-9)
        ci = StatisticalAnalyzer.confidence_interval(b)

        # Pick winner
        winner = None
        winner_type = None
        if sig and uplift > 0:
            winner = treatment.variant_id
            winner_type = treatment.variant_type.value
        elif sig and uplift < 0:
            winner = control.variant_id
            winner_type = control.variant_type.value

        return ExperimentResult(
            experiment_id=exp.experiment_id,
            winner=winner,
            winner_variant_type=winner_type,
            p_value=round(p, 4),
            significant=sig,
            uplift=round(uplift, 4),
            confidence_interval=(round(ci[0], 4), round(ci[1], 4)),
            sample_sizes={control.variant_id: len(a), treatment.variant_id: len(b)},
            metric_means={
                control.variant_id: {m: control.mean(m) for m in control.metrics},
                treatment.variant_id: {m: treatment.mean(m) for m in treatment.metrics}
            },
            duration=(exp.ended_at or time.time()) - (exp.started_at or exp.created_at)
        )


class RolloutManager:
    """Staged rollout with progressive traffic increase and kill switch."""

    def __init__(self):
        self._rollouts: Dict[str, Dict[str, Any]] = {}

    def start(self, experiment_id: str, variant_id: str, stage: RolloutStage = RolloutStage.CANARY) -> None:
        self._rollouts[experiment_id] = {
            "variant_id": variant_id,
            "stage": stage,
            "traffic_pct": stage.value,
            "started_at": time.time(),
            "paused": False,
        }

    def advance(self, experiment_id: str) -> Optional[RolloutStage]:
        r = self._rollouts.get(experiment_id)
        if not r:
            return None
        stages = list(RolloutStage)
        idx = stages.index(r["stage"])
        if idx + 1 < len(stages):
            r["stage"] = stages[idx + 1]
            r["traffic_pct"] = r["stage"].value
            return r["stage"]
        return None

    def pause(self, experiment_id: str) -> None:
        if experiment_id in self._rollouts:
            self._rollouts[experiment_id]["paused"] = True

    def resume(self, experiment_id: str) -> None:
        if experiment_id in self._rollouts:
            self._rollouts[experiment_id]["paused"] = False

    def kill(self, experiment_id: str) -> None:
        self._rollouts.pop(experiment_id, None)

    def is_active(self, experiment_id: str) -> bool:
        r = self._rollouts.get(experiment_id)
        return r is not None and not r.get("paused", False)

    def get_traffic_pct(self, experiment_id: str) -> float:
        r = self._rollouts.get(experiment_id)
        return r["traffic_pct"] if r else 0.0


class ExperimentTracker:
    """Track all experiments and generate reports."""

    def __init__(self):
        self._experiments: Dict[str, Experiment] = {}
        self._results: Dict[str, ExperimentResult] = {}

    def create(self, name: str, hypothesis: str, primary_metric: str = "conversion") -> Experiment:
        eid = str(uuid.uuid4())[:12]
        exp = Experiment(
            experiment_id=eid,
            name=name,
            hypothesis=hypothesis,
            primary_metric=primary_metric,
            variants=[
                Variant(variant_id=f"{eid}-ctrl", name="Control", variant_type=VariantType.CONTROL, weight=0.5),
                Variant(variant_id=f"{eid}-treat", name="Treatment", variant_type=VariantType.TREATMENT, weight=0.5),
            ]
        )
        self._experiments[eid] = exp
        return exp

    def start(self, experiment_id: str) -> bool:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return False
        exp.status = ExperimentStatus.RUNNING
        exp.started_at = time.time()
        return True

    def record(self, experiment_id: str, variant_id: str, metric: str, value: float) -> bool:
        exp = self._experiments.get(experiment_id)
        if not exp or exp.status != ExperimentStatus.RUNNING:
            return False
        for v in exp.variants:
            if v.variant_id == variant_id:
                v.record(metric, value)
                return True
        return False

    def stop(self, experiment_id: str) -> Optional[ExperimentResult]:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return None
        exp.status = ExperimentStatus.COMPLETED
        exp.ended_at = time.time()
        result = StatisticalAnalyzer.analyze_experiment(exp)
        self._results[experiment_id] = result
        return result

    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        return self._experiments.get(experiment_id)

    def get_result(self, experiment_id: str) -> Optional[ExperimentResult]:
        return self._results.get(experiment_id)

    def list_experiments(self) -> List[Experiment]:
        return list(self._experiments.values())

    def export_report(self, path: str) -> None:
        report = {
            "experiments": [e.to_dict() for e in self._experiments.values()],
            "results": {
                k: {
                    "winner": v.winner,
                    "significant": v.significant,
                    "p_value": v.p_value,
                    "uplift": v.uplift,
                    "sample_sizes": v.sample_sizes,
                }
                for k, v in self._results.items()
            }
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("A/B TESTING FRAMEWORK DEMO")
    print("=" * 70)

    # 1. Experiment setup
    print("\n[1] Create Experiment")
    tracker = ExperimentTracker()
    exp = tracker.create("Prompt v2", "New prompt template improves accuracy", primary_metric="accuracy")
    print(f"  Experiment: {exp.experiment_id} — {exp.name}")
    print(f"  Variants: {[v.name for v in exp.variants]}")

    # 2. Traffic splitting
    print("\n[2] Traffic Splitting")
    splitter = TrafficSplitter(salt="magnatrix-2024")
    users = [f"user-{i}" for i in range(1000)]
    distribution = splitter.get_distribution(users, exp.variants)
    print(f"  Distribution: {distribution}")
    # Consistency check
    u = users[0]
    v1 = splitter.deterministic_assign(u, exp.variants)
    v2 = splitter.deterministic_assign(u, exp.variants)
    print(f"  Deterministic consistency: {v1.variant_id == v2.variant_id}")

    # 3. Simulate data collection
    print("\n[3] Simulate Data Collection")
    tracker.start(exp.experiment_id)
    # Control: baseline accuracy ~0.72
    for i in range(200):
        tracker.record(exp.experiment_id, exp.variants[0].variant_id, "accuracy", random.gauss(0.72, 0.05))
    # Treatment: improved accuracy ~0.78
    for i in range(200):
        tracker.record(exp.experiment_id, exp.variants[1].variant_id, "accuracy", random.gauss(0.78, 0.05))
    print(f"  Control samples: {exp.variants[0].count('accuracy')}")
    print(f"  Treatment samples: {exp.variants[1].count('accuracy')}")

    # 4. Statistical analysis
    print("\n[4] Statistical Analysis")
    result = tracker.stop(exp.experiment_id)
    print(f"  Winner: {result.winner}")
    print(f"  Significant: {result.significant}")
    print(f"  P-value: {result.p_value}")
    print(f"  Uplift: {result.uplift:.2%}")
    print(f"  Confidence Interval: {result.confidence_interval}")
    print(f"  Sample sizes: {result.sample_sizes}")

    # 5. Sample size calculator
    print("\n[5] Sample Size Calculator")
    n = StatisticalAnalyzer.required_sample_size(baseline_rate=0.72, mde=0.06, power=0.8, alpha=0.05)
    print(f"  Required per group: {n} (baseline=0.72, MDE=0.06)")

    # 6. Rollout manager
    print("\n[6] Rollout Manager")
    rollout = RolloutManager()
    rollout.start(exp.experiment_id, result.winner or exp.variants[1].variant_id, RolloutStage.CANARY)
    print(f"  Stage: CANARY, traffic: {rollout.get_traffic_pct(exp.experiment_id):.0%}")
    rollout.advance(exp.experiment_id)
    print(f"  Advanced: traffic: {rollout.get_traffic_pct(exp.experiment_id):.0%}")
    rollout.advance(exp.experiment_id)
    print(f"  Advanced: traffic: {rollout.get_traffic_pct(exp.experiment_id):.0%}")
    rollout.pause(exp.experiment_id)
    print(f"  Paused: active={rollout.is_active(exp.experiment_id)}")
    rollout.resume(exp.experiment_id)
    print(f"  Resumed: active={rollout.is_active(exp.experiment_id)}")

    # 7. Multiple experiments
    print("\n[7] Multiple Experiments Tracking")
    exp2 = tracker.create("Model latency", "Smaller model reduces latency", primary_metric="latency_ms")
    tracker.start(exp2.experiment_id)
    for i in range(100):
        tracker.record(exp2.experiment_id, exp2.variants[0].variant_id, "latency_ms", random.gauss(250, 30))
    for i in range(100):
        tracker.record(exp2.experiment_id, exp2.variants[1].variant_id, "latency_ms", random.gauss(180, 25))
    r2 = tracker.stop(exp2.experiment_id)
    print(f"  Exp2 winner: {r2.winner}, significant: {r2.significant}, uplift: {r2.uplift:.2%}")
    print(f"  Total experiments tracked: {len(tracker.list_experiments())}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
