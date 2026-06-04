"""Grover Search — amplitude amplification, oracle, diffusion, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math, random

@dataclass
class GroverSearch:
    n_qubits: int = 3
    marked: List[int] = field(default_factory=list)

    def initialize(self) -> List[float]:
        N = 2 ** self.n_qubits
        return [1 / math.sqrt(N)] * N

    def oracle(self, amplitudes: List[float]) -> List[float]:
        for m in self.marked:
            if 0 <= m < len(amplitudes):
                amplitudes[m] = -amplitudes[m]
        return amplitudes

    def diffusion(self, amplitudes: List[float]) -> List[float]:
        mean = sum(amplitudes) / len(amplitudes)
        return [2 * mean - a for a in amplitudes]

    def iterate(self, amplitudes: List[float], iterations: int) -> List[float]:
        for _ in range(iterations):
            amplitudes = self.oracle(amplitudes)
            amplitudes = self.diffusion(amplitudes)
        return amplitudes

    def measure(self, amplitudes: List[float]) -> int:
        probs = [abs(a)**2 for a in amplitudes]
        r = random.random()
        cum = 0
        for i, p in enumerate(probs):
            cum += p
            if r < cum:
                return i
        return len(amplitudes) - 1

    def optimal_iterations(self) -> int:
        N = 2 ** self.n_qubits
        M = max(len(self.marked), 1)
        return int(round((math.pi / 4) * math.sqrt(N / M)))

    def stats(self) -> Dict:
        return {"n_qubits": self.n_qubits, "marked": len(self.marked), "optimal_iters": self.optimal_iterations()}

def run():
    g = GroverSearch(n_qubits=3, marked=[5])
    amps = g.initialize()
    amps = g.iterate(amps, g.optimal_iterations())
    print("Result:", g.measure(amps))
    print(g.stats())

if __name__ == "__main__":
    run()
