"""Mash Calculator — strike temp, water ratio, gravity, efficiency, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class MashCalculator:
    grain_weight_kg: float = 5.0
    water_ratio: float = 3.0
    """L/kg"""
    target_temp: float = 67.0
    grain_temp: float = 20.0
    efficiency: float = 0.75

    def strike_water_temp(self) -> float:
        return (0.41 / self.water_ratio) * (self.target_temp - self.grain_temp) + self.target_temp

    def water_volume(self) -> float:
        return self.grain_weight_kg * self.water_ratio

    def max_gravity_points(self) -> float:
        return 37 * self.grain_weight_kg

    def expected_og(self, volume_l: float = 25.0) -> float:
        if volume_l <= 0:
            return 1.0
        points = self.max_gravity_points() * self.efficiency
        return 1 + points / (volume_l * 1000)

    def mash_ph_estimate(self, base_ph: float = 5.7) -> float:
        return base_ph - 0.1 * (self.target_temp - 65) / 10

    def stats(self) -> Dict:
        return {"strike_temp": round(self.strike_water_temp(), 1), "water_volume": round(self.water_volume(), 1), "expected_og": round(self.expected_og(), 3)}

def run():
    mc = MashCalculator(grain_weight_kg=4, water_ratio=3, target_temp=65, grain_temp=18, efficiency=0.8)
    print(mc.stats())

if __name__ == "__main__":
    run()
