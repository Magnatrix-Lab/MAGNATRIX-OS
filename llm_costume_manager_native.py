"""Costume Manager — inventory, fitting, budget, rental, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class CostumeManager:
    costumes: List[Dict] = field(default_factory=list)
    rental_rate_per_day: float = 15.0

    def total_cost(self, days: int = 7) -> float:
        return sum(c.get("qty", 1) for c in self.costumes) * self.rental_rate_per_day * days

    def size_breakdown(self) -> Dict:
        if not self.costumes:
            return {}
        sizes = {}
        for c in self.costumes:
            s = c.get("size", "M")
            sizes[s] = sizes.get(s, 0) + c.get("qty", 1)
        return sizes

    def missing_items(self, needed: List[str]) -> List[str]:
        available = {c.get("name", "") for c in self.costumes}
        return [n for n in needed if n not in available]

    def stats(self) -> Dict:
        return {"cost_usd": round(self.total_cost(), 2), "sizes": self.size_breakdown(), "total_qty": sum(c.get("qty", 1) for c in self.costumes)}

def run():
    cm = CostumeManager(costumes=[{"name": "Robe", "size": "L", "qty": 3}, {"name": "Crown", "size": "M", "qty": 1}], rental_rate_per_day=20)
    print(cm.stats())

if __name__ == "__main__":
    run()
