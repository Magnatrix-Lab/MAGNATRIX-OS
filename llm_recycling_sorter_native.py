"""Native stdlib module: Recycling Sorter
Categorizes materials by recyclability and contamination levels.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class Recyclability(Enum):
    RECYCLABLE = "recyclable"
    COMPOSTABLE = "compostable"
    LANDFILL = "landfill"
    SPECIAL = "special"

@dataclass
class MaterialItem:
    name: str
    weight_kg: float
    recyclability: Recyclability
    contamination_pct: float = 0.0

@dataclass
class RecyclingSorter:
    facility_name: str
    items: List[MaterialItem] = field(default_factory=list)

    def total_weight_kg(self) -> float:
        return sum(i.weight_kg for i in self.items)

    def by_category(self) -> Dict[str, float]:
        totals = {}
        for i in self.items:
            totals[i.recyclability.value] = totals.get(i.recyclability.value, 0) + i.weight_kg
        return totals

    def contamination_kg(self) -> float:
        return sum(i.weight_kg * (i.contamination_pct / 100) for i in self.items)

    def contamination_rate_pct(self) -> float:
        if self.total_weight_kg() == 0:
            return 0.0
        return (self.contamination_kg() / self.total_weight_kg()) * 100

    def clean_recyclable_kg(self) -> float:
        return sum(i.weight_kg * (1 - i.contamination_pct / 100) for i in self.items if i.recyclability == Recyclability.RECYCLABLE)

    def stats(self) -> Dict:
        return {
            "facility": self.facility_name,
            "total_weight_kg": round(self.total_weight_kg(), 1),
            "by_category": {k: round(v, 1) for k, v in self.by_category().items()},
            "contamination_rate_pct": round(self.contamination_rate_pct(), 1),
            "clean_recyclable_kg": round(self.clean_recyclable_kg(), 1),
        }

def run():
    rs = RecyclingSorter(
        facility_name="MRF Central",
        items=[
            MaterialItem("PET bottles", 200, Recyclability.RECYCLABLE, 5),
            MaterialItem("cardboard", 150, Recyclability.RECYCLABLE, 3),
            MaterialItem("food_waste", 80, Recyclability.COMPOSTABLE, 0),
            MaterialItem("styrofoam", 40, Recyclability.LANDFILL, 0),
            MaterialItem("batteries", 10, Recyclability.SPECIAL, 0),
        ]
    )
    print(rs.stats())

if __name__ == "__main__":
    run()
