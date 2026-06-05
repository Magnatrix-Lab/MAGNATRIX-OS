"""Native stdlib module: Rolling Stock Calculator
Calculates axle loads, wheel-rail forces, and wear estimates for rolling stock.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class RollingStockCalculator:
    vehicle_mass_ton: float
    num_axles: int
    wheel_diameter_mm: float
    axle_spacing_m: float
    speed_kmh: float

    def axle_load_ton(self) -> float:
        if self.num_axles == 0:
            return 0.0
        return self.vehicle_mass_ton / self.num_axles

    def wheel_load_kn(self) -> float:
        mass_kg = self.vehicle_mass_ton * 1000
        if self.num_axles == 0:
            return 0.0
        return (mass_kg * 9.81) / (self.num_axles * 2)

    def dynamic_augmentation_pct(self) -> float:
        if self.speed_kmh == 0:
            return 0.0
        return min(33, (self.speed_kmh / 100) * 10)

    def wheel_rail_contact_stress_mpa(self) -> float:
        wheel_load = self.wheel_load_kn() * 1000
        if self.wheel_diameter_mm == 0:
            return 0.0
        contact_radius_mm = self.wheel_diameter_mm / 2
        return 0.39 * (wheel_load / contact_radius_mm) ** 0.5

    def wear_index(self) -> float:
        return self.axle_load_ton() * self.speed_kmh / 100

    def stats(self) -> Dict:
        return {
            "axle_load_ton": round(self.axle_load_ton(), 2),
            "wheel_load_kn": round(self.wheel_load_kn(), 2),
            "dynamic_augmentation_pct": round(self.dynamic_augmentation_pct(), 1),
            "contact_stress_mpa": round(self.wheel_rail_contact_stress_mpa(), 2),
            "wear_index": round(self.wear_index(), 2),
        }

def run():
    rsc = RollingStockCalculator(vehicle_mass_ton=80, num_axles=4, wheel_diameter_mm=920, axle_spacing_m=2.8, speed_kmh=120)
    print(rsc.stats())

if __name__ == "__main__":
    run()
