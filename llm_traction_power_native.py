"""Native stdlib module: Traction Power Calculator
Calculates traction power consumption, regeneration, and catenary loads.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class TractionPowerCalculator:
    train_mass_ton: float
    acceleration_m_s2: float
    max_speed_kmh: float
    gradient_pct: float
    efficiency_pct: float = 85.0

    def traction_force_kn(self) -> float:
        mass_kg = self.train_mass_ton * 1000
        gravity_force = mass_kg * 9.81 * (self.gradient_pct / 100)
        acceleration_force = mass_kg * self.acceleration_m_s2
        return (gravity_force + acceleration_force) / 1000

    def power_at_wheels_kw(self) -> float:
        speed_ms = self.max_speed_kmh / 3.6
        return self.traction_force_kn() * speed_ms

    def electrical_power_kw(self) -> float:
        if self.efficiency_pct == 0:
            return 0.0
        return self.power_at_wheels_kw() / (self.efficiency_pct / 100)

    def energy_per_km_kwh(self) -> float:
        if self.max_speed_kmh == 0:
            return 0.0
        time_per_km_hr = 1 / self.max_speed_kmh
        return self.electrical_power_kw() * time_per_km_hr

    def regenerative_energy_pct(self, braking_efficiency_pct: float = 70) -> float:
        return braking_efficiency_pct

    def stats(self) -> Dict:
        return {
            "traction_force_kn": round(self.traction_force_kn(), 1),
            "power_at_wheels_kw": round(self.power_at_wheels_kw(), 1),
            "electrical_power_kw": round(self.electrical_power_kw(), 1),
            "energy_per_km_kwh": round(self.energy_per_km_kwh(), 2),
            "regenerative_energy_pct": self.regenerative_energy_pct(),
        }

def run():
    tpc = TractionPowerCalculator(train_mass_ton=300, acceleration_m_s2=1.0, max_speed_kmh=120, gradient_pct=2, efficiency_pct=88)
    print(tpc.stats())

if __name__ == "__main__":
    run()
