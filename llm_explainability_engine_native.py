"""Explainability Engine — SHAP-style feature importance, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import random
import math

class ExplainMethod(Enum):
    SHAP = auto()
    LIME = auto()
    FEATURE_IMPORTANCE = auto()

@dataclass
class FeatureContribution:
    feature_name: str
    value: float
    contribution: float
    baseline: float

class ExplainabilityEngine:
    def __init__(self, method: ExplainMethod = ExplainMethod.SHAP):
        self.method = method
        self.baseline: Dict[str, float] = {}
        self.explanations: List[Dict] = []

    def set_baseline(self, baseline: Dict[str, float]):
        self.baseline = baseline

    def explain(self, instance: Dict[str, float], prediction: float) -> List[FeatureContribution]:
        if self.method == ExplainMethod.SHAP:
            return self._shap_explain(instance, prediction)
        elif self.method == ExplainMethod.LIME:
            return self._lime_explain(instance, prediction)
        else:
            return self._feature_importance(instance, prediction)

    def _shap_explain(self, instance: Dict[str, float], prediction: float) -> List[FeatureContribution]:
        total = sum(instance.values())
        if total == 0:
            total = 1
        baseline_val = sum(self.baseline.values()) if self.baseline else 0
        contributions = []
        for k, v in instance.items():
            base = self.baseline.get(k, 0)
            contrib = (v - base) / total * (prediction - baseline_val)
            contributions.append(FeatureContribution(k, v, contrib, base))
        return contributions

    def _lime_explain(self, instance: Dict[str, float], prediction: float) -> List[FeatureContribution]:
        samples = []
        for _ in range(50):
            perturbed = {k: v + random.gauss(0, abs(v) * 0.1 + 0.01) for k, v in instance.items()}
            pred = sum(perturbed.values())
            samples.append((perturbed, pred))
        weights = {}
        for k in instance:
            diffs = [(s[1] - prediction) / (s[0][k] - instance[k] + 1e-6) for s in samples if abs(s[0][k] - instance[k]) > 1e-6]
            weights[k] = sum(diffs) / len(diffs) if diffs else 0
        return [FeatureContribution(k, v, weights.get(k, 0) * (v - self.baseline.get(k, 0)), self.baseline.get(k, 0)) for k, v in instance.items()]

    def _feature_importance(self, instance: Dict[str, float], prediction: float) -> List[FeatureContribution]:
        total = sum(abs(v) for v in instance.values())
        if total == 0:
            total = 1
        return [FeatureContribution(k, v, abs(v) / total * prediction, self.baseline.get(k, 0)) for k, v in instance.items()]

    def explain_batch(self, instances: List[Dict]) -> List[List[FeatureContribution]]:
        return [self.explain(inst, sum(inst.values())) for inst in instances]

    def stats(self) -> Dict:
        return {"method": self.method.name, "explanations": len(self.explanations), "baseline_keys": len(self.baseline)}

def run():
    engine = ExplainabilityEngine(ExplainMethod.SHAP)
    engine.set_baseline({"a": 0, "b": 0, "c": 0})
    instance = {"a": 2.0, "b": -1.0, "c": 0.5}
    exp = engine.explain(instance, sum(instance.values()))
    for e in exp:
        print(f"{e.feature_name}: value={e.value:.2f} contrib={e.contribution:.3f}")
    print(engine.stats())

if __name__ == "__main__":
    run()
