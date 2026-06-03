"""GAN Generator - Generator network for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
import random
import math

@dataclass
class GANGenerator:
    latent_dim: int = 2; output_dim: int = 4
    weights: List[List[float]] = field(default_factory=list)

    def __post_init__(self):
        if not self.weights:
            self.weights = [[random.gauss(0, 0.1) for _ in range(self.latent_dim)] for _ in range(self.output_dim)]

    def relu(self, x: float) -> float: return max(0.0, x)

    def generate(self, z: List[float]) -> List[float]:
        return [self.relu(sum(z[j]*self.weights[i][j] for j in range(self.latent_dim))) for i in range(self.output_dim)]

    def stats(self) -> dict:
        return {"latent": self.latent_dim, "output": self.output_dim}

def run():
    gen = GANGenerator(2, 4)
    z = [random.gauss(0,1) for _ in range(2)]
    print("Generated:", [round(v,4) for v in gen.generate(z)])
    print("Stats:", gen.stats())

if __name__ == "__main__": run()
