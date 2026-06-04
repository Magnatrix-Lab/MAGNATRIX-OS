"""Uncertainty Estimator - Epistemic/aleatoric for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum, auto
import math
import random

class UncertaintyType(Enum):
    EPISTEMIC = auto(); ALEATORIC = auto(); TOTAL = auto()

@dataclass
class UncertaintyEstimator:
    uncertainty_type: UncertaintyType = UncertaintyType.TOTAL
    predictions: List[float] = field(default_factory=list)

    def from_ensemble(self, ensemble_preds: List[List[float]]) -> List[float]:
        n = len(ensemble_preds[0])
        means = [sum(p[i] for p in ensemble_preds)/len(ensemble_preds) for i in range(n)]
        if self.uncertainty_type == UncertaintyType.EPISTEMIC:
            return [math.sqrt(sum((p[i]-means[i])**2 for p in ensemble_preds)/len(ensemble_preds)) for i in range(n)]
        elif self.uncertainty_type == UncertaintyType.ALEATORIC:
            return [0.1]*n
        return [math.sqrt(sum((p[i]-means[i])**2 for p in ensemble_preds)/len(ensemble_preds) + 0.01) for i in range(n)]

    def stats(self, ensemble_preds: List[List[float]]) -> dict:
        unc = self.from_ensemble(ensemble_preds)
        return {"type": self.uncertainty_type.name, "mean_uncertainty": round(sum(unc)/len(unc), 4) if unc else 0}

def run():
    ue = UncertaintyEstimator(UncertaintyType.EPISTEMIC)
    preds = [[1.0, 2.0, 3.0], [1.1, 1.9, 3.2], [0.9, 2.1, 2.8]]
    print("Uncertainty:", [round(u, 4) for u in ue.from_ensemble(preds)])
    print("Stats:", ue.stats(preds))

if __name__ == "__main__": run()
