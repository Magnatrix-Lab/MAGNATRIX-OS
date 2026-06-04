#!/usr/bin/env python3
"""MAGNATRIX-OS :: Monte Carlo Simulator Native Module
Runs stochastic simulations using random sampling to estimate outcomes and quantify uncertainty.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Callable, Tuple


class DistributionType(Enum):
    UNIFORM = auto()
    NORMAL = auto()
    TRIANGULAR = auto()
    EXPONENTIAL = auto()
    BETA = auto()


@dataclass
class Variable:
    name: str
    dist_type: DistributionType
    params: List[float]


@dataclass
class SimulationResult:
    iterations: int
    mean: float
    median: float
    std_dev: float
    min_val: float
    max_val: float
    percentile_95: float
    percentile_5: float
    all_samples: List[float] = field(default_factory=list, repr=False)

    def to_dict(self) -> Dict:
        return {
            "iterations": self.iterations,
            "mean": round(self.mean, 4),
            "median": round(self.median, 4),
            "std_dev": round(self.std_dev, 4),
            "min": round(self.min_val, 4),
            "max": round(self.max_val, 4),
            "p95": round(self.percentile_95, 4),
            "p5": round(self.percentile_5, 4),
        }


class MonteCarloSimulator:
    """Stochastic simulation engine using random sampling."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.variables: List[Variable] = []

    def add_variable(self, var: Variable) -> None:
        self.variables.append(var)

    def _sample(self, var: Variable) -> float:
        if var.dist_type == DistributionType.UNIFORM:
            a, b = var.params
            return self.rng.uniform(a, b)
        elif var.dist_type == DistributionType.NORMAL:
            mu, sigma = var.params
            return self.rng.gauss(mu, sigma)
        elif var.dist_type == DistributionType.TRIANGULAR:
            low, high, mode = var.params
            return self.rng.triangular(low, high, mode)
        elif var.dist_type == DistributionType.EXPONENTIAL:
            lambd, = var.params
            return self.rng.expovariate(lambd)
        elif var.dist_type == DistributionType.BETA:
            alpha, beta = var.params
            return self.rng.betavariate(alpha, beta)
        return 0.0

    def run(self, model_func: Callable[[List[float]], float], iterations: int = 10000) -> SimulationResult:
        samples = []
        for _ in range(iterations):
            values = [self._sample(v) for v in self.variables]
            samples.append(model_func(values))
        samples.sort()
        n = len(samples)
        mean = sum(samples) / n
        variance = sum((x - mean) ** 2 for x in samples) / n
        std_dev = math.sqrt(variance)
        median = samples[n // 2] if n % 2 else (samples[n // 2 - 1] + samples[n // 2]) / 2
        p5_idx = int(n * 0.05)
        p95_idx = int(n * 0.95)
        return SimulationResult(
            iterations=iterations,
            mean=mean,
            median=median,
            std_dev=std_dev,
            min_val=samples[0],
            max_val=samples[-1],
            percentile_95=samples[p95_idx],
            percentile_5=samples[p5_idx],
            all_samples=samples,
        )

    def stats(self) -> Dict[str, int]:
        return {"variables": len(self.variables)}


def run() -> None:
    sim = MonteCarloSimulator(seed=42)
    sim.add_variable(Variable("price", DistributionType.NORMAL, [100.0, 15.0]))
    sim.add_variable(Variable("demand", DistributionType.TRIANGULAR, [500.0, 1500.0, 1000.0]))
    sim.add_variable(Variable("cost", DistributionType.UNIFORM, [40.0, 60.0]))

    def profit_model(vals: List[float]) -> float:
        price, demand, cost = vals
        return (price - cost) * demand

    result = sim.run(profit_model, iterations=10000)
    print(f"Monte Carlo Simulator Demo:")
    print(f"  Mean profit: {result.mean:.2f}")
    print(f"  Median: {result.median:.2f}, StdDev: {result.std_dev:.2f}")
    print(f"  95% CI: [{result.percentile_5:.2f}, {result.percentile_95:.2f}]")
    print(f"  Stats: {sim.stats()}")


if __name__ == "__main__":
    run()
