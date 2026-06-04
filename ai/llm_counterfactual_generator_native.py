"""Counterfactual Generator - What-if analysis for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import random

@dataclass
class CounterfactualGenerator:
    features: Dict[str, float] = field(default_factory=dict)
    outcome_model: callable = None

    def __post_init__(self):
        if self.outcome_model is None:
            self.outcome_model = lambda f: f.get("x1", 0) * 2 + f.get("x2", 0) * -1 + 5

    def generate(self, target_outcome: float, n_samples: int = 5) -> List[Dict]:
        results = []
        for _ in range(n_samples):
            cf = self.features.copy()
            cf["x1"] = cf.get("x1", 0) + random.uniform(-1, 1)
            cf["x2"] = cf.get("x2", 0) + random.uniform(-1, 1)
            pred = self.outcome_model(cf)
            if abs(pred - target_outcome) < 0.5:
                results.append({"features": cf, "outcome": pred})
        return results

    def stats(self) -> dict:
        return {"features": len(self.features), "outcome": self.outcome_model(self.features)}

def run():
    cg = CounterfactualGenerator({"x1": 2.0, "x2": 1.0})
    cfs = cg.generate(8.0, 10)
    print("Counterfactuals:", len(cfs))
    print("Stats:", cg.stats())

if __name__ == "__main__": run()
