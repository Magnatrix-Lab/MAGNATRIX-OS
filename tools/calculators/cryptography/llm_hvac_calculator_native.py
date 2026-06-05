"""HVAC Calculator — load, CFM, BTU, efficiency, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class HVACCalculator:
    area_sqft: float = 1000.0
    ceiling_height: float = 8.0
    occupants: int = 4
    windows: int = 4

    def cooling_load(self, factor: float = 25.0) -> float:
        return self.area_sqft * factor

    def heating_load(self, factor: float = 30.0) -> float:
        return self.area_sqft * factor

    def cfm_required(self, ach: float = 6.0) -> float:
        volume = self.area_sqft * self.ceiling_height
        return volume * ach / 60

    def btu_per_sqft(self, load: float) -> float:
        return load / self.area_sqft if self.area_sqft > 0 else 0.0

    def efficiency_rating(self, actual_btu: float, input_btu: float) -> float:
        return actual_btu / input_btu if input_btu > 0 else 0.0

    def stats(self) -> Dict:
        return {"cooling_btu": self.cooling_load(), "cfm": round(self.cfm_required(), 1), "btu_per_sqft": round(self.btu_per_sqft(self.cooling_load()), 1)}

def run():
    hvac = HVACCalculator(area_sqft=2000, occupants=6, windows=8)
    print(hvac.stats())
    print("Heating:", hvac.heating_load())

if __name__ == "__main__":
    run()
