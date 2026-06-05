"""Cupping Scorer — aroma, flavor, body, acidity, balance, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class CuppingScorer:
    fragrance: float = 7.5
    flavor: float = 7.5
    aftertaste: float = 7.5
    acidity: float = 7.5
    body: float = 7.5
    balance: float = 7.5
    sweetness: float = 7.5
    clean_cup: float = 7.5
    uniformity: float = 7.5
    overall: float = 7.5

    def total_score(self) -> float:
        return sum([self.fragrance, self.flavor, self.aftertaste, self.acidity, self.body, self.balance, self.sweetness, self.clean_cup, self.uniformity, self.overall])

    def defects(self, count: int = 0) -> float:
        return count * 2

    def final_score(self, defects: int = 0) -> float:
        return self.total_score() - self.defects(defects)

    def grade(self) -> str:
        s = self.final_score()
        if s >= 90: return "outstanding"
        elif s >= 85: return "excellent"
        elif s >= 80: return "very good"
        elif s >= 75: return "good"
        return "not specialty"

    def stats(self) -> Dict:
        return {"total": round(self.total_score(), 1), "final": round(self.final_score(), 1), "grade": self.grade()}

def run():
    cs = CuppingScorer(fragrance=8, flavor=8.5, aftertaste=8, acidity=7.5, body=8, balance=8, sweetness=8, clean_cup=8, uniformity=7.5, overall=8.5)
    print(cs.stats())

if __name__ == "__main__":
    run()
