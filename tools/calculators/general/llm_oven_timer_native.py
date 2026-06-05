"""Oven Timer — thermal mass, temp, core temp, carryover, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class OvenTimer:
    item_weight_kg: float = 1.0
    oven_temp: float = 200.0
    target_core: float = 75.0
    initial_temp: float = 4.0
    thermal_diffusivity: float = 1e-7

    def estimated_time(self, shape_factor: float = 1.0) -> float:
        thickness = (self.item_weight_kg / 1000) ** (1/3) * 0.1
        return -math.log((self.target_core - self.oven_temp) / (self.initial_temp - self.oven_temp)) * thickness ** 2 / (self.thermal_diffusivity * math.pi ** 2) * shape_factor / 60

    def carryover_rise(self, pull_temp: float) -> float:
        return (self.oven_temp - pull_temp) * 0.05

    def rest_time(self) -> float:
        return self.item_weight_kg * 5

    def probe_placement(self) -> float:
        return self.item_weight_kg ** (1/3) * 2.5

    def stats(self) -> Dict:
        return {"estimated_time": round(self.estimated_time(), 1), "carryover": round(self.carryover_rise(70), 1), "rest": self.rest_time()}

def run():
    ot = OvenTimer(item_weight_kg=2.5, oven_temp=220, target_core=80, initial_temp=10)
    print(ot.stats())
    print("Probe depth:", ot.probe_placement())

if __name__ == "__main__":
    run()
