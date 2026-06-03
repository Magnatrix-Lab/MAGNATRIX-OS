"""Batch Normalizer - Batch normalization for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum, auto
import math

@dataclass
class BatchNormalizer:
    num_features: int = 4
    epsilon: float = 1e-5
    momentum: float = 0.1
    running_mean: List[float] = field(default_factory=list)
    running_var: List[float] = field(default_factory=list)
    gamma: List[float] = field(default_factory=list)
    beta: List[float] = field(default_factory=list)

    def __post_init__(self):
        if not self.running_mean:
            self.running_mean = [0.0] * self.num_features
            self.running_var = [1.0] * self.num_features
            self.gamma = [1.0] * self.num_features
            self.beta = [0.0] * self.num_features

    def normalize(self, batch: List[List[float]], training: bool = True) -> List[List[float]]:
        if training:
            means = [sum(batch[i][j] for i in range(len(batch))) / len(batch) for j in range(self.num_features)]
            vars = [sum((batch[i][j] - means[j])**2 for i in range(len(batch))) / len(batch) for j in range(self.num_features)]
            self.running_mean = [(1-self.momentum)*self.running_mean[j] + self.momentum*means[j] for j in range(self.num_features)]
            self.running_var = [(1-self.momentum)*self.running_var[j] + self.momentum*vars[j] for j in range(self.num_features)]
        else:
            means, vars = self.running_mean, self.running_var
        return [[self.gamma[j] * (batch[i][j] - means[j]) / math.sqrt(vars[j] + self.epsilon) + self.beta[j] for j in range(self.num_features)] for i in range(len(batch))]

    def stats(self) -> dict:
        return {"features": self.num_features, "running_mean": [round(m, 4) for m in self.running_mean]}

def run():
    bn = BatchNormalizer(3)
    batch = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]
    out = bn.normalize(batch)
    print("Normalized:", [[round(v, 4) for v in row] for row in out])
    print("Stats:", bn.stats())

if __name__ == "__main__":
    run()
