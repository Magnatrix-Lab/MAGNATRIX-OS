"""Orthodontic Planner — spacing, overbite, crowding, treatment time, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class OrthodonticPlanner:
    arch_length: float = 80.0
    tooth_material: float = 75.0
    overjet_mm: float = 4.0
    overbite_mm: float = 3.0
    crowding_mm: float = 5.0

    def spacing_needed(self) -> float:
        return max(0, self.arch_length - self.tooth_material)

    def crowding_severity(self) -> str:
        if self.crowding_mm >= 7: return "severe"
        elif self.crowding_mm >= 4: return "moderate"
        elif self.crowding_mm > 0: return "mild"
        return "none"

    def overjet_class(self) -> str:
        if self.overjet_mm >= 6: return "class II"
        elif self.overjet_mm < 0: return "class III"
        return "normal"

    def estimated_treatment_time(self, appliance: str = "fixed") -> float:
        base = 12.0
        if self.crowding_mm > 0:
            base += self.crowding_mm * 2
        if self.overjet_mm > 4:
            base += (self.overjet_mm - 4) * 3
        if appliance == "invisalign":
            base *= 1.2
        elif appliance == "lingual":
            base *= 1.5
        return base

    def extraction_needed(self) -> bool:
        return self.crowding_mm > 7 and self.spacing_needed() <= 0

    def stats(self) -> Dict:
        return {
            "spacing": round(self.spacing_needed(), 1),
            "crowding": self.crowding_severity(),
            "overjet_class": self.overjet_class(),
            "estimated_months": round(self.estimated_treatment_time(), 1),
            "extraction": self.extraction_needed()
        }

def run():
    op = OrthodonticPlanner(arch_length=78, tooth_material=82, overjet_mm=6, crowding_mm=8)
    print(op.stats())

if __name__ == "__main__":
    run()
