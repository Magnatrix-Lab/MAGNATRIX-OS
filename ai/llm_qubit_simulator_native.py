"""Qubit Simulator - Quantum state simulation for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Dict
from enum import Enum, auto
import random
import math
import cmath

class GateType(Enum):
    H = auto(); X = auto(); Y = auto(); Z = auto(); CNOT = auto()

@dataclass
class QubitSimulator:
    num_qubits: int = 2
    state: List[complex] = field(default_factory=list)

    def __post_init__(self):
        if not self.state:
            self.state = [0.0]*(2**self.num_qubits)
            self.state[0] = 1.0

    def apply_h(self, target: int) -> None:
        new_state = [0.0]*len(self.state)
        for i in range(len(self.state)):
            bit = (i >> target) & 1
            j = i ^ (1 << target)
            if bit == 0:
                new_state[i] += (self.state[i] + self.state[j]) / math.sqrt(2)
            else:
                new_state[i] += (self.state[i] - self.state[j]) / math.sqrt(2)
        self.state = new_state

    def apply_x(self, target: int) -> None:
        for i in range(len(self.state)):
            j = i ^ (1 << target)
            if i < j:
                self.state[i], self.state[j] = self.state[j], self.state[i]

    def measure(self, shots: int = 100) -> Dict[int, int]:
        probs = [abs(self.state[i])**2 for i in range(len(self.state))]
        results = {}
        for _ in range(shots):
            r = random.random(); cum = 0
            for i, p in enumerate(probs):
                cum += p
                if r < cum:
                    results[i] = results.get(i, 0) + 1
                    break
        return results

    def stats(self) -> dict:
        probs = [round(abs(s)**2, 4) for s in self.state]
        return {"qubits": self.num_qubits, "states": len(self.state), "probs": probs}

def run():
    qs = QubitSimulator(2)
    qs.apply_h(0)
    print("Measure:", qs.measure(50))
    print("Stats:", qs.stats())

if __name__ == "__main__": run()
