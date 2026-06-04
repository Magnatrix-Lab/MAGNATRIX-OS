"""Network Diffusion - Diffusion models on networks for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
from enum import Enum, auto
import random

class DiffusionModel(Enum):
    SI = auto(); SIR = auto(); INDEPENDENT_CASCADE = auto()

@dataclass
class NetworkDiffusion:
    model: DiffusionModel = DiffusionModel.SIR
    beta: float = 0.3
    gamma: float = 0.1

    def simulate_sir(self, edges: Dict[str, List[str]], initial_infected: Set[str], steps: int = 10) -> List[Dict[str, int]]:
        S = set(edges.keys()) - initial_infected
        I = set(initial_infected)
        R = set()
        history = [{"S": len(S), "I": len(I), "R": len(R)}]
        for _ in range(steps):
            new_I = set()
            new_R = set()
            for node in I:
                if random.random() < self.gamma:
                    new_R.add(node)
                for neighbor in edges.get(node, []):
                    if neighbor in S and random.random() < self.beta:
                        new_I.add(neighbor)
            I = (I - new_R) | new_I
            S = S - new_I
            R = R | new_R
            history.append({"S": len(S), "I": len(I), "R": len(R)})
        return history

    def stats(self, edges: Dict[str, List[str]], initial_infected: Set[str]) -> dict:
        history = self.simulate_sir(edges, initial_infected, 10)
        return {"model": self.model.name, "final_infected": history[-1]["I"] if history else 0, "peak": max(h["I"] for h in history) if history else 0}

def run():
    nd = NetworkDiffusion(DiffusionModel.SIR, 0.3, 0.1)
    edges = {"A": ["B", "C"], "B": ["A", "C"], "C": ["A", "B", "D"], "D": ["C"], "E": ["D"]}
    history = nd.simulate_sir(edges, {"A"}, 10)
    print("Final:", history[-1])
    print("Stats:", nd.stats(edges, {"A"}))

if __name__ == "__main__": run()
