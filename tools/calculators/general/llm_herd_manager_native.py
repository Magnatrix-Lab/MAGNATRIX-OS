"""Herd Manager — inventory, culling, replacement, economics, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class HerdAnimal:
    id: str
    age_months: int
    production: float
    health_status: str = "good"
    pregnant: bool = False

class HerdManager:
    def __init__(self):
        self.animals: List[HerdAnimal] = []
        self.cull_threshold_age: int = 84
        self.cull_threshold_production: float = 0.7

    def add_animal(self, a: HerdAnimal):
        self.animals.append(a)

    def cull_list(self) -> List[str]:
        to_cull = []
        max_prod = max(a.production for a in self.animals) if self.animals else 1
        for a in self.animals:
            if a.age_months > self.cull_threshold_age:
                to_cull.append(a.id)
            elif a.production < max_prod * self.cull_threshold_production:
                to_cull.append(a.id)
            elif a.health_status == "poor":
                to_cull.append(a.id)
        return to_cull

    def replacement_needed(self, target_size: int) -> int:
        return max(0, target_size - len(self.animals) + len(self.cull_list()))

    def average_production(self) -> float:
        return sum(a.production for a in self.animals) / len(self.animals) if self.animals else 0.0

    def economic_value(self, milk_price: float = 0.5, cull_value: float = 300) -> float:
        prod_value = sum(a.production for a in self.animals) * milk_price
        cull_revenue = len(self.cull_list()) * cull_value
        return prod_value + cull_revenue

    def age_distribution(self) -> Dict[int, int]:
        dist = {}
        for a in self.animals:
            bucket = a.age_months // 12
            dist[bucket] = dist.get(bucket, 0) + 1
        return dist

    def stats(self) -> Dict:
        return {
            "total": len(self.animals),
            "to_cull": len(self.cull_list()),
            "avg_production": round(self.average_production(), 2),
            "age_dist": self.age_distribution()
        }

def run():
    hm = HerdManager()
    hm.add_animal(HerdAnimal("H1", 36, 25))
    hm.add_animal(HerdAnimal("H2", 90, 18))
    hm.add_animal(HerdAnimal("H3", 48, 22, health_status="poor"))
    hm.add_animal(HerdAnimal("H4", 24, 28))
    print(hm.stats())
    print("Replacement needed (target 100):", hm.replacement_needed(100))

if __name__ == "__main__":
    run()
