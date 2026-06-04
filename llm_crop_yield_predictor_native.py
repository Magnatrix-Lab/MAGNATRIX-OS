"""Crop Yield Predictor — regression, soil, weather, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class CropYieldPredictor:
    soil_quality: float = 0.5
    rainfall: float = 500.0
    temperature: float = 25.0
    fertilizer: float = 100.0
    area: float = 10.0

    def yield_per_hectare(self) -> float:
        base = 2000.0
        soil_factor = 1 + (self.soil_quality - 0.5)
        rain_factor = 1 - abs(self.rainfall - 600) / 1000
        temp_factor = 1 - abs(self.temperature - 22) / 20
        fert_factor = 1 + math.log(self.fertilizer + 1) / 10
        return base * soil_factor * rain_factor * temp_factor * fert_factor

    def total_yield(self) -> float:
        return self.yield_per_hectare() * self.area

    def optimize_fertilizer(self) -> float:
        best = 0.0
        best_yield = 0.0
        for f in range(0, 500, 10):
            self.fertilizer = f
            y = self.yield_per_hectare()
            if y > best_yield:
                best_yield = y
                best = f
        return best

    def stats(self) -> Dict:
        return {"yield_per_ha": round(self.yield_per_hectare(), 2), "total": round(self.total_yield(), 2)}

def run():
    cyp = CropYieldPredictor(soil_quality=0.7, rainfall=600, temperature=22, fertilizer=150, area=20)
    print(cyp.stats())
    print("Optimal fertilizer:", cyp.optimize_fertilizer())

if __name__ == "__main__":
    run()
