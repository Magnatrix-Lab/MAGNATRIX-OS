"""Byzantine Robust Aggregator - Robust aggregation for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math
import random

class RobustMethod(Enum):
    KRUM = auto(); MULTI_KRUM = auto(); GEO_MEDIAN = auto()

@dataclass
class ByzantineRobustAggregator:
    method: RobustMethod = RobustMethod.KRUM
    f: int = 1

    def distance(self, a: List[float], b: List[float]) -> float:
        return math.sqrt(sum((a[i]-b[i])**2 for i in range(len(a))))

    def krum(self, updates: List[List[float]]) -> List[float]:
        n = len(updates)
        scores = []
        for i in range(n):
            dists = sorted(self.distance(updates[i], updates[j]) for j in range(n) if i != j)
            score = sum(dists[:n-self.f-2])
            scores.append((score, i))
        return updates[min(scores, key=lambda x: x[0])[1]]

    def geo_median(self, updates: List[List[float]], max_iter: int = 10) -> List[float]:
        dim = len(updates[0])
        median = [sum(u[i] for u in updates)/len(updates) for i in range(dim)]
        for _ in range(max_iter):
            weights = [1.0 / (self.distance(median, u) + 1e-6) for u in updates]
            total = sum(weights)
            median = [sum(u[i]*w for u,w in zip(updates, weights))/total for i in range(dim)]
        return median

    def aggregate(self, updates: List[List[float]]) -> List[float]:
        if self.method == RobustMethod.KRUM: return self.krum(updates)
        elif self.method == RobustMethod.GEO_MEDIAN: return self.geo_median(updates)
        return [sum(u[i] for u in updates)/len(updates) for i in range(len(updates[0]))]

    def stats(self, updates: List[List[float]]) -> dict:
        return {"method": self.method.name, "clients": len(updates), "f": self.f}

def run():
    bra = ByzantineRobustAggregator(RobustMethod.KRUM, 1)
    updates = [[1.0, 2.0], [1.1, 2.1], [0.9, 1.9], [100.0, -100.0]]
    agg = bra.aggregate(updates)
    print("Aggregated:", [round(v, 4) for v in agg])
    print("Stats:", bra.stats(updates))

if __name__ == "__main__": run()
