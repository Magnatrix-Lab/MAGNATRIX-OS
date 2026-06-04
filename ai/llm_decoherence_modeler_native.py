"""Decoherence Modeler - Noise simulation for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum, auto
import random
import math

class NoiseType(Enum):
    DEPOLARIZING = auto(); AMPLITUDE_DAMPING = auto(); PHASE_DAMPING = auto()

@dataclass
class DecoherenceModeler:
    noise_type: NoiseType = NoiseType.DEPOLARIZING
    probability: float = 0.01

    def apply(self, state: List[complex]) -> List[complex]:
        if self.noise_type == NoiseType.DEPOLARIZING:
            return [(1-self.probability)*s + self.probability*0.25*sum(state) for s in state]
        elif self.noise_type == NoiseType.AMPLITUDE_DAMPING:
            return [s if random.random() > self.probability else 0 for s in state]
        return state

    def purity(self, state: List[complex]) -> float:
        return sum(abs(s)**2 for s in state)**2

    def stats(self, state: List[complex]) -> dict:
        noisy = self.apply(state)
        return {"type": self.noise_type.name, "prob": self.probability, "purity_before": round(self.purity(state), 4), "purity_after": round(self.purity(noisy), 4)}

def run():
    dm = DecoherenceModeler(NoiseType.DEPOLARIZING, 0.05)
    state = [1/math.sqrt(2), 0, 0, 1/math.sqrt(2)]
    print("Stats:", dm.stats(state))

if __name__ == "__main__": run()
