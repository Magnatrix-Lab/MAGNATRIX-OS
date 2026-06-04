"""Explainability Engine - LIME-style explanations for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import random
import math

@dataclass
class ExplainabilityEngine:
    feature_names: List[str] = field(default_factory=list)

    def explain(self, instance: List[float], predictor: callable, num_samples: int = 50) -> List[Tuple[str, float]]:
        base_pred = predictor(instance)
        importances = []
        for i in range(len(instance)):
            diffs = []
            for _ in range(num_samples):
                perturbed = instance[:]
                perturbed[i] += random.gauss(0, 0.1)
                new_pred = predictor(perturbed)
                diffs.append(abs(new_pred - base_pred))
            importances.append((self.feature_names[i] if i < len(self.feature_names) else f"feat_{i}", sum(diffs)/len(diffs)))
        return sorted(importances, key=lambda x: x[1], reverse=True)

    def stats(self, instance: List[float], predictor: callable) -> dict:
        exp = self.explain(instance, predictor, 20)
        return {"top_feature": exp[0][0] if exp else None, "importance": round(exp[0][1], 4) if exp else 0}

def run():
    ee = ExplainabilityEngine(["age", "income", "score"])
    def predictor(x): return x[0] * 2 + x[1] * 0.5 + x[2] * 1.5
    print("Explain:", ee.explain([30, 50000, 700], predictor, 20))
    print("Stats:", ee.stats([30, 50000, 700], predictor))

if __name__ == "__main__": run()
