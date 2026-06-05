"""Active Learning — uncertainty sampling, query strategy, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math
import random

class QueryStrategy(Enum):
    UNCERTAINTY = auto()
    DIVERSITY = auto()
    RANDOM = auto()

@dataclass
class UnlabeledSample:
    sample_id: str
    features: Dict[str, float]
    uncertainty: float = 0.0
    selected: bool = False

class ActiveLearner:
    def __init__(self, strategy: QueryStrategy = QueryStrategy.UNCERTAINTY, budget: int = 10):
        self.strategy = strategy
        self.budget = budget
        self.labeled: List[Dict] = []
        self.unlabeled: List[UnlabeledSample] = []
        self.model_weights: Dict[str, float] = {}
        self.selection_history: List[str] = []

    def add_unlabeled(self, samples: List[Dict[str, float]]):
        for i, s in enumerate(samples):
            self.unlabeled.append(UnlabeledSample(f"u{i}", s))

    def _compute_uncertainty(self, sample: UnlabeledSample) -> float:
        score = sum(sample.features.get(k, 0) * self.model_weights.get(k, 0) for k in set(sample.features) | set(self.model_weights))
        return 1.0 - abs(score)

    def _compute_diversity(self, sample: UnlabeledSample) -> float:
        if not self.labeled:
            return random.random()
        distances = []
        for l in self.labeled:
            dist = sum((sample.features.get(k, 0) - l.get("features", {}).get(k, 0)) ** 2 for k in set(sample.features) | set(l.get("features", {})))
            distances.append(math.sqrt(dist))
        return min(distances) if distances else 0

    def select_samples(self, n: int = 5) -> List[UnlabeledSample]:
        for u in self.unlabeled:
            if self.strategy == QueryStrategy.UNCERTAINTY:
                u.uncertainty = self._compute_uncertainty(u)
            elif self.strategy == QueryStrategy.DIVERSITY:
                u.uncertainty = self._compute_diversity(u)
            else:
                u.uncertainty = random.random()
        sorted_samples = sorted(self.unlabeled, key=lambda x: x.uncertainty, reverse=True)
        selected = sorted_samples[:n]
        for s in selected:
            s.selected = True
            self.selection_history.append(s.sample_id)
        return selected

    def label_sample(self, sample_id: str, label: Any):
        for u in self.unlabeled:
            if u.sample_id == sample_id:
                self.labeled.append({"sample_id": sample_id, "features": u.features, "label": label})
                self.unlabeled.remove(u)
                break

    def stats(self) -> Dict:
        return {"strategy": self.strategy.name, "labeled": len(self.labeled), "unlabeled": len(self.unlabeled), "selected": len(self.selection_history), "budget_left": self.budget - len(self.labeled)}

def run():
    learner = ActiveLearner(strategy=QueryStrategy.UNCERTAINTY, budget=20)
    samples = [{f"f{i}": random.random() for i in range(5)} for _ in range(20)]
    learner.add_unlabeled(samples)
    learner.model_weights = {f"f{i}": random.gauss(0, 0.5) for i in range(5)}
    selected = learner.select_samples(5)
    print("Selected:", [s.sample_id for s in selected])
    print(learner.stats())

if __name__ == "__main__":
    run()
