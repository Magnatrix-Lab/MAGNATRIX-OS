"""Monte Carlo Simulator - Random sampling for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Callable
from enum import Enum, auto
import random
import math

class MCType(Enum):
    INTEGRATION = auto(); ESTIMATION = auto(); SIMULATION = auto()

@dataclass
class MonteCarloSimulator:
    mc_type: MCType = MCType.INTEGRATION
    n_samples: int = 10000

    def estimate_pi(self) -> float:
        inside = 0
        for _ in range(self.n_samples):
            x, y = random.random(), random.random()
            if x*x + y*y <= 1: inside += 1
        return 4 * inside / self.n_samples

    def integrate(self, f: Callable, a: float, b: float) -> float:
        total = sum(f(random.uniform(a, b)) for _ in range(self.n_samples))
        return (b - a) * total / self.n_samples

    def estimate_mean(self, samples: List[float]) -> Tuple[float, float]:
        mean = sum(samples) / len(samples)
        variance = sum((x - mean)**2 for x in samples) / len(samples)
        return mean, math.sqrt(variance / len(samples))

    def stats(self) -> dict:
        return {"type": self.mc_type.name, "samples": self.n_samples, "pi_estimate": round(self.estimate_pi(), 6)}

def run():
    mc = MonteCarloSimulator(MCType.INTEGRATION, 5000)
    print("Pi estimate:", round(mc.estimate_pi(), 6))
    integral = mc.integrate(lambda x: x**2, 0, 1)
    print("Integral x^2:", round(integral, 6))
    print("Stats:", mc.stats())

if __name__ == "__main__": run()
