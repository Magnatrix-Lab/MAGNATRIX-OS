"""Native stdlib module: Herb Garden Planner
Plans garden layout by spacing, sunlight, and companion planting rules.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class SunRequirement(Enum):
    FULL = "full"
    PARTIAL = "partial"
    SHADE = "shade"

@dataclass
class HerbSpec:
    name: str
    spacing_cm: float
    sun: SunRequirement
    companions: List[str] = field(default_factory=list)

@dataclass
class HerbGardenPlanner:
    garden_width_m: float
    garden_length_m: float
    herbs: List[HerbSpec] = field(default_factory=list)

    def area_m2(self) -> float:
        return self.garden_width_m * self.garden_length_m

    def max_plants(self, herb: HerbSpec) -> int:
        area_cm2 = self.area_m2() * 10000
        plant_area_cm2 = herb.spacing_cm ** 2
        if plant_area_cm2 == 0:
            return 0
        return int(area_cm2 / plant_area_cm2)

    def sunlight_zones(self) -> Dict[str, int]:
        zones = {"full": 0, "partial": 0, "shade": 0}
        for h in self.herbs:
            zones[h.sun.value] += 1
        return zones

    def stats(self) -> Dict:
        return {
            "area_m2": round(self.area_m2(), 2),
            "herb_types": len(self.herbs),
            "sunlight_zones": self.sunlight_zones(),
        }

def run():
    hgp = HerbGardenPlanner(
        garden_width_m=3, garden_length_m=5,
        herbs=[
            HerbSpec("basil", 30, SunRequirement.FULL, ["tomato", "oregano"]),
            HerbSpec("mint", 45, SunRequirement.PARTIAL, ["cabbage", "tomato"]),
            HerbSpec("parsley", 20, SunRequirement.PARTIAL, ["rose", "tomato"]),
            HerbSpec("thyme", 25, SunRequirement.FULL, ["strawberry", "cabbage"]),
            HerbSpec("chives", 15, SunRequirement.FULL, ["carrot", "tomato"]),
        ]
    )
    print(hgp.stats())
    for h in hgp.herbs:
        print(f"  {h.name}: max {hgp.max_plants(h)} plants")

if __name__ == "__main__":
    run()
