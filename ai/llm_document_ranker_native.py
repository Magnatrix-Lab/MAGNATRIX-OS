"""Document Ranker - Learning to rank for documents for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math

class RankMethod(Enum):
    POINTWISE = auto(); PAIRWISE = auto(); LISTWISE = auto()

@dataclass
class DocumentRanker:
    method: RankMethod = RankMethod.POINTWISE
    weights: List[float] = field(default_factory=list)

    def fit(self, features: List[List[float]], labels: List[int]) -> None:
        if self.method == RankMethod.POINTWISE:
            n = len(features[0])
            self.weights = [0.0] * n
            for _ in range(100):
                for f, y in zip(features, labels):
                    pred = sum(self.weights[i] * f[i] for i in range(n))
                    err = pred - y
                    for i in range(n):
                        self.weights[i] -= 0.01 * err * f[i]

    def rank(self, features: List[List[float]]) -> List[int]:
        scores = [sum(self.weights[i] * f[i] for i in range(len(f))) for f in features]
        return sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    def stats(self) -> dict:
        return {"method": self.method.name, "weights": [round(w, 4) for w in self.weights]}

def run():
    dr = DocumentRanker(RankMethod.POINTWISE)
    features = [[1, 0, 1], [0, 1, 0], [1, 1, 1], [0, 0, 1]]
    labels = [3, 1, 4, 2]
    dr.fit(features, labels)
    print("Rank:", dr.rank(features))
    print("Stats:", dr.stats())

if __name__ == "__main__": run()
