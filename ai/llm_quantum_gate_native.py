"""Quantum Gate - Gate matrix operations for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum, auto
import cmath
import math

class GateName(Enum):
    H = auto(); X = auto(); Y = auto(); Z = auto(); S = auto(); T = auto()

@dataclass
class QuantumGate:
    name: GateName = GateName.H
    matrix: List[List[complex]] = field(default_factory=list)

    def __post_init__(self):
        if not self.matrix:
            if self.name == GateName.H:
                self.matrix = [[1/math.sqrt(2), 1/math.sqrt(2)], [1/math.sqrt(2), -1/math.sqrt(2)]]
            elif self.name == GateName.X:
                self.matrix = [[0, 1], [1, 0]]
            elif self.name == GateName.Y:
                self.matrix = [[0, -1j], [1j, 0]]
            elif self.name == GateName.Z:
                self.matrix = [[1, 0], [0, -1]]
            elif self.name == GateName.S:
                self.matrix = [[1, 0], [0, 1j]]
            elif self.name == GateName.T:
                self.matrix = [[1, 0], [0, cmath.exp(1j*math.pi/4)]]

    def apply(self, state: List[complex]) -> List[complex]:
        return [sum(self.matrix[i][j]*state[j] for j in range(len(state))) for i in range(len(self.matrix))]

    def stats(self) -> dict:
        return {"name": self.name.name, "dim": len(self.matrix)}

def run():
    for g in [GateName.H, GateName.X, GateName.Z]:
        gate = QuantumGate(g)
        out = gate.apply([1, 0])
        print(f"{g.name}: {[round(abs(v)**2, 4) for v in out]}")
    print("Stats:", QuantumGate().stats())

if __name__ == "__main__": run()
