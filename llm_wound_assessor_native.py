"""Wound Assessor — PUSH, size, healing, infection, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class WoundAssessor:
    length_cm: float = 2.0
    width_cm: float = 1.5
    depth_cm: float = 0.5
    exudate_amount: int = 2
    """0-4"""
    tissue_type: int = 3
    """0-4, 4 is closed"""

    def area(self) -> float:
        return self.length_cm * self.width_cm

    def volume(self) -> float:
        return self.area() * self.depth_cm

    def push_score(self) -> int:
        return self.exudate_amount + self.tissue_type

    def healing_rate(self, previous_area: float, days: int) -> float:
        if previous_area <= 0 or days <= 0:
            return 0.0
        return (previous_area - self.area()) / days

    def healing_status(self) -> str:
        if self.tissue_type >= 4: return "healed"
        elif self.tissue_type >= 3: return "granulating"
        elif self.tissue_type >= 2: return "sloughy"
        return "necrotic"

    def infection_risk(self, fever: bool = False, odor: bool = False, erythema: bool = False) -> str:
        signs = sum([fever, odor, erythema, self.exudate_amount >= 3])
        if signs >= 3: return "high"
        elif signs >= 2: return "moderate"
        return "low"

    def stats(self, previous_area: float = 5.0, days: int = 7) -> Dict:
        return {
            "area": round(self.area(), 2),
            "volume": round(self.volume(), 3),
            "push": self.push_score(),
            "status": self.healing_status(),
            "healing_rate": round(self.healing_rate(previous_area, days), 2)
        }

def run():
    wa = WoundAssessor(length_cm=3, width_cm=2, depth_cm=0.8, exudate_amount=3, tissue_type=2)
    print(wa.stats())
    print("Infection risk:", wa.infection_risk(fever=True, odor=True))

if __name__ == "__main__":
    run()
