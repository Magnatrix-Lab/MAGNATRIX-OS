"""Building Code Checker — compliance, fire safety, egress, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class BuildingCodeChecker:
    occupancy: int = 50
    floor_area_m2: float = 200.0
    stories: int = 1

    def egress_doors(self) -> int:
        return max(1, math.ceil(self.occupancy / 50.0))

    def exit_distance(self) -> float:
        return 45.0 if self.stories <= 1 else 30.0

    def fire_rating_min(self) -> float:
        return 1.0 if self.stories <= 2 else 2.0

    def compliance(self) -> bool:
        return self.egress_doors() >= 1 and self.floor_area_m2 > 0

    def stats(self) -> Dict:
        return {"egress_doors": self.egress_doors(), "exit_distance_m": self.exit_distance(), "fire_rating_h": self.fire_rating_min()}

def run():
    bcc = BuildingCodeChecker(occupancy=120, floor_area_m2=400, stories=2)
    print(bcc.stats())

if __name__ == "__main__":
    run()
