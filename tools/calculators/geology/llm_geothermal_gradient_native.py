"""Native stdlib module: Geothermal Gradient Calculator
Calculates geothermal gradients, heat flow, and subsurface temperatures.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class GeothermalGradientCalculator:
    surface_temperature_c: float
    depth_m: float
    gradient_c_per_km: float = 25.0
    thermal_conductivity_w_m_k: float = 2.5

    def temperature_at_depth_c(self) -> float:
        return self.surface_temperature_c + (self.depth_m / 1000) * self.gradient_c_per_km

    def heat_flow_mw_m2(self) -> float:
        return self.gradient_c_per_km * self.thermal_conductivity_w_m_k

    def depth_for_temperature_c(self, target_temp_c: float) -> float:
        if self.gradient_c_per_km == 0:
            return 0.0
        temp_diff = target_temp_c - self.surface_temperature_c
        return (temp_diff / self.gradient_c_per_km) * 1000

    def boiling_depth_m(self) -> float:
        return self.depth_for_temperature_c(100)

    def stats(self) -> Dict:
        return {
            "surface_temp_c": self.surface_temperature_c,
            "depth_m": self.depth_m,
            "temp_at_depth_c": round(self.temperature_at_depth_c(), 1),
            "heat_flow_mw_m2": round(self.heat_flow_mw_m2(), 1),
            "boiling_depth_m": round(self.boiling_depth_m(), 1),
        }

def run():
    gc = GeothermalGradientCalculator(surface_temperature_c=15, depth_m=3000, gradient_c_per_km=30, thermal_conductivity_w_m_k=2.8)
    print(gc.stats())

if __name__ == "__main__":
    run()
