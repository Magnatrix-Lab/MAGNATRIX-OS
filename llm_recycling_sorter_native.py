"""Recycling Sorter -- purity, contamination, bale value, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class RecyclingSorter:
    stream: str = "mixed"
    items: List[Dict] = field(default_factory=list)

    def purity(self) -> float:
        if not self.items:
            return 0.0
        correct = sum(1 for i in self.items if i.get("correct_stream", False))
        return correct / len(self.items)

    def contamination_rate(self) -> float:
        return 1 - self.purity()

    def bale_value(self, price_per_ton: float) -> float:
        total_weight = sum(i.get("weight_kg", 0) for i in self.items) / 1000
        return total_weight * price_per_ton * self.purity()

    def sort_efficiency(self, target_purity: float = 0.95) -> float:
        return min(1.0, self.purity() / target_purity)

    def reject_items(self) -> List[str]:
        return [i.get("id", "") for i in self.items if not i.get("correct_stream", False)]

    def stats(self) -> Dict:
        return {"items": len(self.items), "purity": round(self.purity(), 3), "contamination": round(self.contamination_rate(), 3), "efficiency": round(self.sort_efficiency(), 3)}

def run():
    rs = RecyclingSorter("PET", [
        {"id": "1", "weight_kg": 0.5, "correct_stream": True},
        {"id": "2", "weight_kg": 0.3, "correct_stream": True},
        {"id": "3", "weight_kg": 0.2, "correct_stream": False},
    ])
    print(rs.stats())
    print("Rejects:", rs.reject_items())

if __name__ == "__main__":
    run()
