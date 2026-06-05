"""Geotechnical Calculator — bearing capacity, settlement, slope stability, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class GeotechnicalCalculator:
    cohesion: float = 25.0
    friction_angle: float = 30.0
    soil_density: float = 18.0
    foundation_width: float = 2.0

    def terzaghi_bearing(self, depth: float = 1.0) -> float:
        phi = math.radians(self.friction_angle)
        Nq = math.exp(math.pi * math.tan(phi)) * math.tan(math.radians(45 + self.friction_angle / 2)) ** 2
        Nc = (Nq - 1) / math.tan(phi) if math.tan(phi) > 0 else 0
        Ng = 2 * (Nq + 1) * math.tan(phi)
        q = self.soil_density * depth
        return q * Nq + self.cohesion * Nc + 0.5 * self.soil_density * self.foundation_width * Ng

    def settlement(self, load: float, compressibility: float = 0.0001) -> float:
        return load * compressibility * self.foundation_width

    def factor_of_safety(self, slope_angle: float, slope_height: float) -> float:
        phi = math.radians(self.friction_angle)
        theta = math.radians(slope_angle)
        if math.sin(theta) == 0:
            return float('inf')
        return (self.cohesion + self.soil_density * slope_height * math.cos(theta) * math.tan(phi)) / (self.soil_density * slope_height * math.sin(theta))

    def stats(self, depth: float = 1.0) -> Dict:
        return {"bearing_capacity": round(self.terzaghi_bearing(depth), 1), "settlement_mm": round(self.settlement(100) * 1000, 2)}

def run():
    gc = GeotechnicalCalculator(cohesion=30, friction_angle=35, soil_density=20)
    print(gc.stats())
    print("FOS slope 30°:", gc.factor_of_safety(30, 5))

if __name__ == "__main__":
    run()
