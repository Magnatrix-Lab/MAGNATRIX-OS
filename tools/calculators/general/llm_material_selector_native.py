"""Material Selector — durability, cost, sustainability, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class MaterialSelector:
    materials: List[Dict] = field(default_factory=list)

    def best_value(self) -> Optional[Dict]:
        if not self.materials:
            return None
        scored = [(m, m.get("durability", 0) / (m.get("cost", 1) + 0.001)) for m in self.materials]
        return max(scored, key=lambda x: x[1])[0]

    def total_cost(self, quantities: List[float]) -> float:
        return sum(m.get("cost", 0) * q for m, q in zip(self.materials, quantities))

    def sustainability_score(self) -> float:
        if not self.materials:
            return 0.0
        return sum(m.get("eco_score", 0) for m in self.materials) / len(self.materials)

    def stats(self) -> Dict:
        return {"best_value": self.best_value(), "sustainability": round(self.sustainability_score(), 2)}

def run():
    ms = MaterialSelector(materials=[{"name": "Oak", "durability": 9, "cost": 50, "eco_score": 8}, {"name": "Pine", "durability": 6, "cost": 20, "eco_score": 7}])
    print(ms.stats())

if __name__ == "__main__":
    run()
