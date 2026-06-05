"""Root System — architecture, depth, spread, uptake, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class RootSystem:
    max_depth: float = 1.0
    spread_radius: float = 0.5
    root_length: float = 100.0
    fine_root_pct: float = 0.6

    def root_volume(self, avg_radius: float = 0.002) -> float:
        return math.pi * avg_radius**2 * self.root_length

    def root_surface_area(self, avg_radius: float = 0.002) -> float:
        return 2 * math.pi * avg_radius * self.root_length

    def uptake_capacity(self, soil_moisture: float) -> float:
        surface = self.root_surface_area()
        return surface * soil_moisture * 0.1

    def root_shoot_ratio(self, shoot_mass: float) -> float:
        root_mass = self.root_volume() * 0.15
        return root_mass / shoot_mass if shoot_mass > 0 else 0.0

    def exploration_efficiency(self, soil_volume: float) -> float:
        root_vol = self.root_volume()
        return root_vol / soil_volume if soil_volume > 0 else 0.0

    def stats(self, soil_moisture: float = 0.3) -> Dict:
        return {"volume": round(self.root_volume(), 4), "surface_area": round(self.root_surface_area(), 2), "uptake": round(self.uptake_capacity(soil_moisture), 2)}

def run():
    rs = RootSystem(max_depth=2, spread_radius=1, root_length=500, fine_root_pct=0.7)
    print(rs.stats())
    print("R/S ratio at 100g shoot:", rs.root_shoot_ratio(100))

if __name__ == "__main__":
    run()
