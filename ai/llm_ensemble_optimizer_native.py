"""Ensemble Optimizer - Weighted ensemble for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum, auto
import math

class EnsembleType(Enum):
    VOTING = auto(); STACKING = auto(); BOOSTING = auto()

@dataclass
class EnsembleOptimizer:
    ensemble_type: EnsembleType = EnsembleType.VOTING
    weights: List[float] = field(default_factory=list)

    def fit(self, predictions: List[List[float]], actual: List[float]) -> None:
        n = len(predictions)
        if self.ensemble_type == EnsembleType.VOTING:
            self.weights = [1.0/n]*n
        elif self.ensemble_type == EnsembleType.STACKING:
            errors = [sum(abs(p[i]-actual[i]) for i in range(len(actual))) for p in predictions]
            total = sum(1.0/(e+1e-6) for e in errors)
            self.weights = [(1.0/(e+1e-6))/total for e in errors]

    def predict(self, predictions: List[List[float]]) -> List[float]:
        n = len(predictions[0])
        return [sum(self.weights[i] * predictions[i][j] for i in range(len(predictions))) for j in range(n)]

    def stats(self) -> dict:
        return {"type": self.ensemble_type.name, "weights": [round(w, 4) for w in self.weights]}

def run():
    eo = EnsembleOptimizer(EnsembleType.STACKING)
    preds = [[1.0, 2.0, 3.0], [1.1, 1.9, 3.1], [0.9, 2.1, 2.9]]
    actual = [1.0, 2.0, 3.0]
    eo.fit(preds, actual)
    print("Predicted:", [round(v, 4) for v in eo.predict(preds)])
    print("Stats:", eo.stats())

if __name__ == "__main__": run()
