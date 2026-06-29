
"""
fitness_evaluator_native.py
MAGNATRIX-OS — Fitness Evaluator

Multi-dimensional fitness evaluation for evolved agents.
Inspired by A-Evolve benchmark scoring across diverse domains.
Pure Python standard library.
"""

import math
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum, auto


class FitnessDimension(Enum):
    ACCURACY = auto()
    SPEED = auto()
    ROBUSTNESS = auto()
    GENERALIZATION = auto()
    EFFICIENCY = auto()
    CREATIVITY = auto()
    SAFETY = auto()
    COST = auto()


@dataclass
class FitnessScore:
    overall: float = 0.0
    dimensions: Dict[str, float] = field(default_factory=dict)
    weights: Dict[str, float] = field(default_factory=dict)
    raw_scores: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        default_weights = {
            "accuracy": 0.35,
            "speed": 0.15,
            "robustness": 0.15,
            "generalization": 0.10,
            "efficiency": 0.10,
            "creativity": 0.10,
            "safety": 0.05,
        }
        for k, v in default_weights.items():
            self.weights.setdefault(k, v)


class FitnessEvaluator:
    """Multi-dimensional fitness evaluation engine."""

    def __init__(self):
        self.evaluators: Dict[str, Callable] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.evaluators["accuracy"] = self._eval_accuracy
        self.evaluators["speed"] = self._eval_speed
        self.evaluators["robustness"] = self._eval_robustness
        self.evaluators["generalization"] = self._eval_generalization
        self.evaluators["efficiency"] = self._eval_efficiency

    def register(self, dimension: str, evaluator: Callable) -> None:
        self.evaluators[dimension] = evaluator

    def evaluate(self, genome, tasks: Optional[List[Dict]] = None,
                 custom_weights: Optional[Dict[str, float]] = None) -> FitnessScore:
        """Evaluate a genome across all fitness dimensions."""
        score = FitnessScore()
        if custom_weights:
            score.weights.update(custom_weights)

        for dimension, evaluator in self.evaluators.items():
            try:
                dim_score = evaluator(genome, tasks or [])
                score.dimensions[dimension] = dim_score
            except Exception:
                score.dimensions[dimension] = 0.0

        # Calculate weighted overall score
        total_weight = 0.0
        weighted_sum = 0.0
        for dim, val in score.dimensions.items():
            w = score.weights.get(dim, 0.1)
            weighted_sum += val * w
            total_weight += w

        score.overall = weighted_sum / total_weight if total_weight > 0 else 0.0
        return score

    def _eval_accuracy(self, genome, tasks: List[Dict]) -> float:
        """Task completion accuracy."""
        if not tasks:
            return 0.5
        skills = getattr(genome, "skills", {})
        passed = sum(1 for t in tasks if t.get("required_skill") in skills)
        return passed / len(tasks)

    def _eval_speed(self, genome, tasks: List[Dict]) -> float:
        """Inference/execution speed efficiency."""
        hyperparams = getattr(genome, "hyperparams", {})
        max_tokens = hyperparams.get("max_tokens", 2048)
        timeout = hyperparams.get("timeout", 60)
        # Lower max_tokens + lower timeout = faster
        token_eff = 1.0 - min(max_tokens / 8192, 1.0)
        timeout_eff = 1.0 - min(timeout / 300, 1.0)
        return (token_eff + timeout_eff) / 2

    def _eval_robustness(self, genome, tasks: List[Dict]) -> float:
        """Error handling and retry capability."""
        skills = getattr(genome, "skills", {})
        has_error_handling = "error-handling" in skills
        has_retry = "retry-logic" in skills
        has_validation = "validation" in skills
        return sum([has_error_handling, has_retry, has_validation]) / 3.0

    def _eval_generalization(self, genome, tasks: List[Dict]) -> float:
        """Ability to handle unseen tasks."""
        skills = getattr(genome, "skills", {})
        # More diverse skills = better generalization
        diversity = len(set(skills.keys())) / max(len(skills), 1)
        return min(diversity, 1.0)

    def _eval_efficiency(self, genome, tasks: List[Dict]) -> float:
        """Resource usage efficiency."""
        hyperparams = getattr(genome, "hyperparams", {})
        retries = hyperparams.get("retries", 3)
        # Fewer retries + caching = more efficient
        retry_eff = max(0, 1.0 - (retries - 1) * 0.2)
        has_cache = "caching" in getattr(genome, "skills", {})
        cache_bonus = 0.2 if has_cache else 0.0
        return min(retry_eff + cache_bonus, 1.0)

    def rank(self, genomes: List, tasks: Optional[List[Dict]] = None) -> List[Dict]:
        """Rank genomes by fitness score."""
        ranked = []
        for g in genomes:
            score = self.evaluate(g, tasks)
            ranked.append({"genome": g, "score": score})
        ranked.sort(key=lambda x: x["score"].overall, reverse=True)
        return ranked


__all__ = ["FitnessEvaluator", "FitnessScore", "FitnessDimension"]
