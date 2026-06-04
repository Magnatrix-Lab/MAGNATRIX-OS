"""Robustness Tester - Adversarial robustness for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import random

class PerturbationType(Enum):
    GAUSSIAN = auto(); UNIFORM = auto(); SALT_PEPPER = auto()

@dataclass
class RobustnessTester:
    perturbation: PerturbationType = PerturbationType.GAUSSIAN
    epsilon: float = 0.1

    def perturb(self, input_data: List[float]) -> List[float]:
        if self.perturbation == PerturbationType.GAUSSIAN:
            return [x + random.gauss(0, self.epsilon) for x in input_data]
        elif self.perturbation == PerturbationType.UNIFORM:
            return [x + random.uniform(-self.epsilon, self.epsilon) for x in input_data]
        elif self.perturbation == PerturbationType.SALT_PEPPER:
            return [x if random.random() > self.epsilon else (0 if random.random() < 0.5 else 1) for x in input_data]
        return input_data

    def test_robustness(self, model: callable, input_data: List[float], true_label: any, n_trials: int = 100) -> float:
        correct = 0
        for _ in range(n_trials):
            perturbed = self.perturb(input_data)
            if model(perturbed) == true_label:
                correct += 1
        return correct / n_trials

    def stats(self, model: callable, input_data: List[float], true_label: any) -> dict:
        acc = self.test_robustness(model, input_data, true_label, 50)
        return {"perturbation": self.perturbation.name, "accuracy": round(acc, 4), "epsilon": self.epsilon}

def run():
    rt = RobustnessTester(PerturbationType.GAUSSIAN, 0.1)
    def model(x): return 1 if sum(x) > 0.5 else 0
    print("Robustness:", round(rt.test_robustness(model, [0.6, 0.7, 0.8], 1, 50), 4))
    print("Stats:", rt.stats(model, [0.6, 0.7, 0.8], 1))

if __name__ == "__main__": run()
