"""Native stdlib module: Micronutrient Tracker
Tracks vitamin and mineral intake against RDAs.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Nutrient:
    name: str
    intake_mg: float
    rda_mg: float
    unit: str = "mg"

@dataclass
class MicronutrientTracker:
    person_name: str
    day: str
    nutrients: List[Nutrient] = field(default_factory=list)

    def pct_of_rda(self, nutrient: Nutrient) -> float:
        if nutrient.rda_mg == 0:
            return 0.0
        return (nutrient.intake_mg / nutrient.rda_mg) * 100

    def adequate(self, nutrient: Nutrient) -> bool:
        return self.pct_of_rda(nutrient) >= 100

    def deficient_nutrients(self) -> List[str]:
        return [n.name for n in self.nutrients if not self.adequate(n)]

    def excess_nutrients(self) -> List[str]:
        return [n.name for n in self.nutrients if self.pct_of_rda(n) > 200]

    def overall_score(self) -> float:
        if not self.nutrients:
            return 0.0
        return sum(min(100, self.pct_of_rda(n)) for n in self.nutrients) / len(self.nutrients)

    def stats(self) -> Dict:
        return {
            "person": self.person_name,
            "day": self.day,
            "nutrients_count": len(self.nutrients),
            "deficient": self.deficient_nutrients(),
            "excess": self.excess_nutrients(),
            "overall_score_pct": round(self.overall_score(), 1),
        }

def run():
    mt = MicronutrientTracker(
        person_name="Alice",
        day="2024-06-05",
        nutrients=[
            Nutrient("Vitamin C", 85, 90, "mg"),
            Nutrient("Vitamin D", 15, 20, "mcg"),
            Nutrient("Iron", 12, 18, "mg"),
            Nutrient("Calcium", 950, 1000, "mg"),
            Nutrient("Zinc", 10, 11, "mg"),
        ]
    )
    print(mt.stats())

if __name__ == "__main__":
    run()
