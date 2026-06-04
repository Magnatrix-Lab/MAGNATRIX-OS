"""Privacy Preserver - Differential privacy for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum, auto
import random
import math

class NoiseMechanism(Enum):
    LAPLACE = auto(); GAUSSIAN = auto()

@dataclass
class PrivacyPreserver:
    epsilon: float = 1.0
    mechanism: NoiseMechanism = NoiseMechanism.LAPLACE

    def add_noise(self, value: float, sensitivity: float = 1.0) -> float:
        if self.mechanism == NoiseMechanism.LAPLACE:
            scale = sensitivity / self.epsilon
            u = random.random() - 0.5
            noise = -scale * math.copysign(1.0, u) * math.log(1 - 2 * abs(u))
            return value + noise
        elif self.mechanism == NoiseMechanism.GAUSSIAN:
            scale = sensitivity / self.epsilon
            return value + random.gauss(0, scale)
        return value

    def noisy_mean(self, data: List[float], sensitivity: float = 1.0) -> float:
        true_mean = sum(data) / len(data) if data else 0
        return self.add_noise(true_mean, sensitivity / len(data) if data else 0)

    def stats(self, data: List[float]) -> dict:
        noisy = self.noisy_mean(data)
        true = sum(data) / len(data) if data else 0
        return {"epsilon": self.epsilon, "true_mean": round(true, 4), "noisy_mean": round(noisy, 4), "error": round(abs(noisy - true), 4)}

def run():
    pp = PrivacyPreserver(1.0, NoiseMechanism.LAPLACE)
    data = [10, 12, 11, 13, 10, 12, 11, 14, 13, 12]
    print("Noisy mean:", round(pp.noisy_mean(data), 4))
    print("Stats:", pp.stats(data))

if __name__ == "__main__": run()
