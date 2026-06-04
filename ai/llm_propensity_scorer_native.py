"""Propensity Scorer - Propensity matching for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import math

@dataclass
class PropensityScorer:
    scores: List[float] = field(default_factory=list)
    treated: List[int] = field(default_factory=list)

    def match(self, caliper: float = 0.1) -> List[Tuple[int, int]]:
        treated_idx = [i for i, t in enumerate(self.treated) if t == 1]
        control_idx = [i for i, t in enumerate(self.treated) if t == 0]
        matches = []
        for ti in treated_idx:
            best = None; best_diff = float('inf')
            for ci in control_idx:
                diff = abs(self.scores[ti] - self.scores[ci])
                if diff < best_diff and diff <= caliper:
                    best_diff = diff; best = ci
            if best is not None: matches.append((ti, best))
        return matches

    def add(self, score: float, is_treated: int) -> None:
        self.scores.append(score); self.treated.append(is_treated)

    def stats(self) -> dict:
        return {"n": len(self.scores), "treated": sum(self.treated), "control": len(self.treated)-sum(self.treated)}

def run():
    ps = PropensityScorer()
    for i in range(10):
        ps.add(i/10.0, 1 if i < 5 else 0)
    print("Matches:", ps.match(0.2))
    print("Stats:", ps.stats())

if __name__ == "__main__": run()
