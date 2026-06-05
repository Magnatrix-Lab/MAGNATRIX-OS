"""Multi-Criteria Decision Analysis — AHP, TOPSIS, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum, auto
import math

class MCDAMethod(Enum):
    AHP = auto()
    TOPSIS = auto()
    WSM = auto()

@dataclass
class Alternative:
    name: str
    criteria: Dict[str, float]

class MCDAAnalyzer:
    def __init__(self, method: MCDAMethod = MCDAMethod.TOPSIS):
        self.method = method
        self.alternatives: List[Alternative] = []
        self.weights: Dict[str, float] = {}
        self.ranking: List[Tuple[str, float]] = []

    def add_alternative(self, name: str, criteria: Dict[str, float]):
        self.alternatives.append(Alternative(name, criteria))

    def set_weights(self, weights: Dict[str, float]):
        self.weights = weights

    def run_ahp(self) -> List[Tuple[str, float]]:
        scores = []
        for alt in self.alternatives:
            score = sum(alt.criteria.get(k, 0) * self.weights.get(k, 0) for k in set(alt.criteria) | set(self.weights))
            scores.append((alt.name, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        self.ranking = scores
        return scores

    def run_topsis(self) -> List[Tuple[str, float]]:
        criteria = list(self.weights.keys())
        if not criteria:
            return []
        # Normalize
        norm = {}
        for c in criteria:
            vals = [alt.criteria.get(c, 0) for alt in self.alternatives]
            s = math.sqrt(sum(v**2 for v in vals))
            norm[c] = [v / s if s else 0 for v in vals]
        # Weighted normalized
        weighted = {}
        for c in criteria:
            weighted[c] = [v * self.weights.get(c, 0) for v in norm[c]]
        # Ideal best/worst
        best = {c: max(weighted[c]) for c in criteria}
        worst = {c: min(weighted[c]) for c in criteria}
        scores = []
        for i, alt in enumerate(self.alternatives):
            d_best = math.sqrt(sum((weighted[c][i] - best[c])**2 for c in criteria))
            d_worst = math.sqrt(sum((weighted[c][i] - worst[c])**2 for c in criteria))
            score = d_worst / (d_best + d_worst) if (d_best + d_worst) > 0 else 0
            scores.append((alt.name, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        self.ranking = scores
        return scores

    def run_wsm(self) -> List[Tuple[str, float]]:
        return self.run_ahp()

    def analyze(self) -> List[Tuple[str, float]]:
        if self.method == MCDAMethod.AHP or self.method == MCDAMethod.WSM:
            return self.run_ahp()
        return self.run_topsis()

    def stats(self) -> Dict:
        return {"method": self.method.name, "alternatives": len(self.alternatives), "criteria": len(self.weights), "top": self.ranking[:3] if self.ranking else []}

def run():
    analyzer = MCDAAnalyzer(MCDAMethod.TOPSIS)
    analyzer.set_weights({"cost": 0.4, "quality": 0.3, "speed": 0.2, "risk": 0.1})
    analyzer.add_alternative("A", {"cost": 500, "quality": 8, "speed": 7, "risk": 3})
    analyzer.add_alternative("B", {"cost": 400, "quality": 7, "speed": 9, "risk": 4})
    analyzer.add_alternative("C", {"cost": 600, "quality": 9, "speed": 6, "risk": 2})
    print(analyzer.analyze())
    print(analyzer.stats())

if __name__ == "__main__":
    run()
