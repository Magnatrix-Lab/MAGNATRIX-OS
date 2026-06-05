"""Binding Selector -- durability, layflat, cost, page count, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class BindingSelector:
    page_count: int = 48
    usage: str = "reference"
    budget: str = "medium"
    layflat_required: bool = False

    def recommendations(self) -> List[str]:
        recs = []
        if self.page_count <= 48 and self.budget in ["low", "medium"]:
            recs.append("saddle_stitch")
        if self.page_count >= 40 and self.budget in ["medium", "high"]:
            recs.append("perfect_bind")
        if self.layflat_required or self.usage in ["manual", "cookbook"]:
            recs.append("spiral")
        if self.page_count >= 100 and self.budget == "high":
            recs.append("hardcover")
        if self.usage in ["premium", "collectible"]:
            recs.append("case_bind")
        return recs if recs else ["perfect_bind"]

    def durability_score(self, binding: str) -> int:
        scores = {"saddle_stitch": 3, "perfect_bind": 5, "spiral": 4, "hardcover": 9, "case_bind": 10, "wire_o": 7}
        return scores.get(binding, 5)

    def cost_score(self, binding: str) -> int:
        scores = {"saddle_stitch": 2, "perfect_bind": 4, "spiral": 5, "hardcover": 9, "case_bind": 10, "wire_o": 6}
        return scores.get(binding, 5)

    def best_match(self) -> str:
        candidates = self.recommendations()
        if self.budget == "low":
            return min(candidates, key=lambda b: self.cost_score(b))
        elif self.usage in ["reference", "premium"]:
            return max(candidates, key=lambda b: self.durability_score(b))
        return candidates[0]

    def stats(self) -> Dict:
        return {"page_count": self.page_count, "recommendations": self.recommendations(), "best_match": self.best_match()}

def run():
    bs = BindingSelector(120, "reference", "high", True)
    print(bs.stats())

if __name__ == "__main__":
    run()
