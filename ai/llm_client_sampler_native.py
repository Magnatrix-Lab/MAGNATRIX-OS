"""Client Sampler - Client selection for FL for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Set
from enum import Enum, auto
import random

class SampleMethod(Enum):
    RANDOM = auto(); UNIFORM = auto(); IMPORTANCE = auto()

@dataclass
class ClientSampler:
    method: SampleMethod = SampleMethod.RANDOM
    fraction: float = 0.1

    def sample(self, clients: List[str], weights: Dict[str, float] = None) -> List[str]:
        k = max(1, int(len(clients) * self.fraction))
        if self.method == SampleMethod.RANDOM:
            return random.sample(clients, k)
        elif self.method == SampleMethod.UNIFORM:
            return random.sample(clients, k)
        elif self.method == SampleMethod.IMPORTANCE and weights:
            sorted_clients = sorted(clients, key=lambda c: weights.get(c, 0), reverse=True)
            return sorted_clients[:k]
        return clients[:k]

    def stats(self, clients: List[str]) -> dict:
        sampled = self.sample(clients)
        return {"method": self.method.name, "total": len(clients), "sampled": len(sampled), "fraction": self.fraction}

def run():
    cs = ClientSampler(SampleMethod.RANDOM, 0.3)
    clients = [f"client_{i}" for i in range(10)]
    sampled = cs.sample(clients)
    print("Sampled:", sampled)
    print("Stats:", cs.stats(clients))

if __name__ == "__main__": run()
