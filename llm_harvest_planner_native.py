"""Native stdlib module: Harvest Planner
Plans fish harvest schedules, yield projections, and size grading.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class SizeGrade:
    min_weight_g: float
    max_weight_g: float
    count: int
    price_per_kg: float

@dataclass
class HarvestPlanner:
    species: str
    total_count: int
    avg_weight_g: float
    size_grades: List[SizeGrade] = field(default_factory=list)

    def total_biomass_kg(self) -> float:
        return self.total_count * self.avg_weight_g / 1000

    def graded_biomass_kg(self) -> float:
        return sum(g.count * ((g.min_weight_g + g.max_weight_g) / 2) / 1000 for g in self.size_grades)

    def ungraded_count(self) -> int:
        graded = sum(g.count for g in self.size_grades)
        return max(0, self.total_count - graded)

    def revenue(self) -> float:
        return sum(g.count * ((g.min_weight_g + g.max_weight_g) / 2) / 1000 * g.price_per_kg for g in self.size_grades)

    def stats(self) -> Dict:
        return {
            "species": self.species,
            "total_count": self.total_count,
            "total_biomass_kg": round(self.total_biomass_kg(), 1),
            "graded_biomass_kg": round(self.graded_biomass_kg(), 1),
            "ungraded_count": self.ungraded_count(),
            "revenue": round(self.revenue(), 2),
            "grades": len(self.size_grades),
        }

def run():
    hp = HarvestPlanner(
        species="Shrimp",
        total_count=50000,
        avg_weight_g=25,
        size_grades=[
            SizeGrade(30, 40, 10000, 12.0),
            SizeGrade(20, 30, 20000, 9.0),
            SizeGrade(10, 20, 15000, 6.0),
        ]
    )
    print(hp.stats())

if __name__ == "__main__":
    run()
