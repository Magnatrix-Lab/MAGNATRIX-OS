"""Bayesian Optimizer - Gaussian process acquisition for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math
import random

class AcquisitionType(Enum):
    UCB = auto(); EI = auto(); PI = auto()

@dataclass
class BayesianOptimizer:
    acquisition: AcquisitionType = AcquisitionType.UCB
    kappa: float = 2.0
    observations: List[Tuple[float, float]] = field(default_factory=list)

    def observe(self, x: float, y: float) -> None:
        self.observations.append((x, y))

    def mean(self, x: float) -> float:
        if not self.observations: return 0.0
        nearby = [y for ox, y in self.observations if abs(ox - x) < 1.0]
        return sum(nearby)/len(nearby) if nearby else 0.0

    def std(self, x: float) -> float:
        if len(self.observations) < 2: return 1.0
        nearby = [y for ox, y in self.observations if abs(ox - x) < 1.0]
        if len(nearby) < 2: return 1.0
        m = sum(nearby)/len(nearby)
        return math.sqrt(sum((y-m)**2 for y in nearby)/(len(nearby)-1))

    def acquisition_value(self, x: float) -> float:
        mu = self.mean(x); sigma = self.std(x)
        if self.acquisition == AcquisitionType.UCB:
            return mu + self.kappa * sigma
        elif self.acquisition == AcquisitionType.EI:
            best = max(y for _, y in self.observations) if self.observations else 0
            return max(0, mu - best) if sigma == 0 else (mu - best) * (1 + math.erf((mu - best)/(sigma * math.sqrt(2))))/2 + sigma * math.exp(-(mu - best)**2/(2*sigma**2))/math.sqrt(2*math.pi)
        return mu

    def suggest(self, candidates: List[float]) -> float:
        return max(candidates, key=lambda x: self.acquisition_value(x))

    def stats(self) -> dict:
        return {"observations": len(self.observations), "acquisition": self.acquisition.name}

def run():
    bo = BayesianOptimizer(AcquisitionType.UCB, 2.0)
    bo.observe(0.0, 1.0); bo.observe(1.0, 2.0); bo.observe(2.0, 1.5)
    candidates = [0.5, 1.5, 2.5]
    print("Suggest:", bo.suggest(candidates))
    print("Stats:", bo.stats())

if __name__ == "__main__": run()
