"""Differential Privacy FL - DP in federated learning for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import random
import math

@dataclass
class DifferentialPrivacyFL:
    epsilon: float = 1.0
    delta: float = 1e-5
    max_grad_norm: float = 1.0

    def clip(self, grad: List[float]) -> List[float]:
        norm = math.sqrt(sum(g*g for g in grad))
        scale = min(1.0, self.max_grad_norm / (norm + 1e-6))
        return [g * scale for g in grad]

    def add_noise(self, grad: List[float], sensitivity: float) -> List[float]:
        sigma = sensitivity * math.sqrt(2 * math.log(1.25 / self.delta)) / self.epsilon
        return [g + random.gauss(0, sigma) for g in grad]

    def privatize(self, grad: List[float]) -> List[float]:
        clipped = self.clip(grad)
        return self.add_noise(clipped, self.max_grad_norm)

    def stats(self, grad: List[float]) -> dict:
        priv = self.privatize(grad)
        return {"epsilon": self.epsilon, "delta": self.delta, "noise_added": round(sum(abs(p-g) for p,g in zip(priv, grad))/len(grad), 6)}

def run():
    dpfl = DifferentialPrivacyFL(1.0, 1e-5, 1.0)
    grad = [0.5, -0.3, 0.8, -0.1]
    priv = dpfl.privatize(grad)
    print("Private:", [round(v, 4) for v in priv])
    print("Stats:", dpfl.stats(grad))

if __name__ == "__main__": run()
