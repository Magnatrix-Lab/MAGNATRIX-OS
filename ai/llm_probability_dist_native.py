"""Probability Distribution - PDF/CDF sampling for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List
from enum import Enum, auto
import math
import random

class DistType(Enum):
    NORMAL = auto(); UNIFORM = auto(); EXPONENTIAL = auto(); BERNOULLI = auto()

@dataclass
class ProbabilityDistribution:
    dist_type: DistType = DistType.NORMAL
    mean: float = 0.0; std: float = 1.0; rate: float = 1.0; p: float = 0.5

    def pdf(self, x: float) -> float:
        if self.dist_type == DistType.NORMAL:
            return (1/(self.std*math.sqrt(2*math.pi))) * math.exp(-0.5*((x-self.mean)/self.std)**2)
        if self.dist_type == DistType.EXPONENTIAL and x >= 0:
            return self.rate * math.exp(-self.rate*x)
        return 0.0

    def sample(self, n: int = 1) -> List[float]:
        if self.dist_type == DistType.NORMAL:
            return [random.gauss(self.mean, self.std) for _ in range(n)]
        if self.dist_type == DistType.UNIFORM:
            return [random.uniform(self.mean-self.std, self.mean+self.std) for _ in range(n)]
        if self.dist_type == DistType.EXPONENTIAL:
            return [random.expovariate(self.rate) for _ in range(n)]
        if self.dist_type == DistType.BERNOULLI:
            return [1.0 if random.random() < self.p else 0.0 for _ in range(n)]
        return []

    def stats(self) -> dict:
        return {"type": self.dist_type.name, "mean": self.mean, "std": self.std}

def run():
    for dt in [DistType.NORMAL, DistType.EXPONENTIAL]:
        d = ProbabilityDistribution(dt, mean=0, std=1, rate=1.0)
        s = d.sample(5)
        print(f"{dt.name}: samples={[round(v,4) for v in s]}")
    print("Stats:", ProbabilityDistribution().stats())

if __name__ == "__main__": run()
