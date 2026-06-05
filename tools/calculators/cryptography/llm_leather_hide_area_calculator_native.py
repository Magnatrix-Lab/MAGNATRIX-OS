"""Native stdlib module: Leather Hide Area Calculator
Calculates hide area, yield, and project feasibility from raw hides.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class LeatherHideAreaCalculator:
    hide_area_sqft: float
    hide_grade: str  # a, b, c, garment
    project_pieces: int
    piece_area_sqft: float

    _YIELD_PCT = {"a": 0.85, "b": 0.75, "c": 0.65, "garment": 0.90}

    def usable_area_sqft(self) -> float:
        return self.hide_area_sqft * self._YIELD_PCT.get(self.hide_grade, 0.75)

    def total_piece_area_sqft(self) -> float:
        return self.project_pieces * self.piece_area_sqft

    def hides_needed(self) -> int:
        if self.usable_area_sqft() == 0:
            return 0
        return (self.total_piece_area_sqft() + self.usable_area_sqft() - 1) // self.usable_area_sqft()

    def waste_pct(self) -> float:
        usable = self.usable_area_sqft() * self.hides_needed()
        if usable == 0:
            return 0
        return (1 - self.total_piece_area_sqft() / usable) * 100

    def efficiency_score(self) -> float:
        return max(0, 100 - self.waste_pct())

    def leftover_area_sqft(self) -> float:
        return self.usable_area_sqft() * self.hides_needed() - self.total_piece_area_sqft()

    def stats(self) -> Dict:
        return {
            "hide_area_sqft": self.hide_area_sqft,
            "hide_grade": self.hide_grade,
            "usable_area_sqft": round(self.usable_area_sqft(), 1),
            "total_piece_area_sqft": round(self.total_piece_area_sqft(), 1),
            "hides_needed": self.hides_needed(),
            "waste_pct": round(self.waste_pct(), 1),
            "efficiency_score": round(self.efficiency_score(), 1),
            "leftover_area_sqft": round(self.leftover_area_sqft(), 1),
        }

def run():
    lhac = LeatherHideAreaCalculator(hide_area_sqft=20, hide_grade="a", project_pieces=8, piece_area_sqft=1.5)
    print(lhac.stats())

if __name__ == "__main__":
    run()
