"""Federated Aggregator - Secure aggregation for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import random
import math

class AggMethod(Enum):
    FEDAVG = auto(); MEDIAN = auto(); TRIMMED_MEAN = auto()

@dataclass
class FederatedAggregator:
    method: AggMethod = AggMethod.FEDAVG

    def aggregate(self, updates: List[List[float]], weights: List[float] = None) -> List[float]:
        if not updates: return []
        dim = len(updates[0])
        if weights is None: weights = [1.0/len(updates)] * len(updates)
        if self.method == AggMethod.FEDAVG:
            return [sum(u[i]*w for u, w in zip(updates, weights)) for i in range(dim)]
        elif self.method == AggMethod.MEDIAN:
            return [sorted(u[i] for u in updates)[len(updates)//2] for i in range(dim)]
        elif self.method == AggMethod.TRIMMED_MEAN:
            trim = max(1, len(updates)//5)
            return [sum(sorted(u[i] for u in updates)[trim:-trim])/(len(updates)-2*trim) for i in range(dim)]
        return []

    def stats(self, updates: List[List[float]]) -> dict:
        return {"method": self.method.name, "clients": len(updates), "dim": len(updates[0]) if updates else 0}

def run():
    fa = FederatedAggregator(AggMethod.FEDAVG)
    updates = [[1.0, 2.0], [1.1, 2.1], [0.9, 1.9]]
    agg = fa.aggregate(updates)
    print("Aggregated:", [round(v, 4) for v in agg])
    print("Stats:", fa.stats(updates))

if __name__ == "__main__": run()
