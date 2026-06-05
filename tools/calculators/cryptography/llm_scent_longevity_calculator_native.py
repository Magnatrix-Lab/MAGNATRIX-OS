"""Native stdlib module: Scent Longevity Calculator
Estimates longevity, sillage, and projection based on composition.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class ScentLongevityCalculator:
    base_note_pct: float
    alcohol_pct: float = 80.0
    skin_type: str = "normal"  # dry, normal, oily
    application_area: str = "pulse_points"  # pulse_points, clothing, hair
    temperature_c: float = 22.0

    def longevity_hours(self) -> float:
        base = self.base_note_pct * 0.4
        alcohol_factor = 1 - (self.alcohol_pct - 70) * 0.005
        skin_factor = {"dry": 0.8, "normal": 1.0, "oily": 1.2}.get(self.skin_type, 1.0)
        area_factor = {"pulse_points": 1.0, "clothing": 1.5, "hair": 0.8}.get(self.application_area, 1.0)
        temp_factor = max(0.7, 1 - (self.temperature_c - 20) * 0.02)
        return base * alcohol_factor * skin_factor * area_factor * temp_factor

    def sillage_score(self) -> float:
        alcohol_bonus = (self.alcohol_pct - 70) * 0.5
        base_malus = self.base_note_pct * 0.1
        return max(0, min(100, 50 + alcohol_bonus - base_malus))

    def projection_meters(self) -> float:
        return self.sillage_score() / 50

    def longevity_category(self) -> str:
        hours = self.longevity_hours()
        if hours < 2:
            return "fleeting"
        elif hours < 4:
            return "moderate"
        elif hours < 8:
            return "long_lasting"
        elif hours < 12:
            return "very_long"
        return "eternal"

    def reapplication_hours(self) -> float:
        return max(1, self.longevity_hours() * 0.7)

    def stats(self) -> Dict:
        return {
            "base_note_pct": self.base_note_pct,
            "alcohol_pct": self.alcohol_pct,
            "skin_type": self.skin_type,
            "application_area": self.application_area,
            "longevity_hours": round(self.longevity_hours(), 1),
            "sillage_score": round(self.sillage_score(), 1),
            "projection_m": round(self.projection_meters(), 2),
            "longevity_category": self.longevity_category(),
            "reapplication_hours": round(self.reapplication_hours(), 1),
        }

def run():
    slc = ScentLongevityCalculator(base_note_pct=30, alcohol_pct=80, skin_type="oily", application_area="pulse_points", temperature_c=25)
    print(slc.stats())

if __name__ == "__main__":
    run()
