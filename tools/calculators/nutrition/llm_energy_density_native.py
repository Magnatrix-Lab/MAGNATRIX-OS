"""Energy Density Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class EnergyDensity:
    mass_kg: float
    volume_liters: float
    nominal_capacity_ah: float
    nominal_voltage_v: float

    def gravimetric_energy_density_wh_per_kg(self) -> float:
        if self.mass_kg <= 0:
            return 0.0
        energy = self.nominal_capacity_ah * self.nominal_voltage_v
        return round(energy / self.mass_kg, 2)

    def volumetric_energy_density_wh_per_l(self) -> float:
        if self.volume_liters <= 0:
            return 0.0
        energy = self.nominal_capacity_ah * self.nominal_voltage_v
        return round(energy / self.volume_liters, 2)

    def mass_energy_ratio_kg_per_kwh(self) -> float:
        wh = self.gravimetric_energy_density_wh_per_kg()
        if wh <= 0:
            return 0.0
        return round(1000 / wh, 3)

    def volume_per_kwh_liters(self) -> float:
        wh = self.volumetric_energy_density_wh_per_l()
        if wh <= 0:
            return 0.0
        return round(1000 / wh, 3)

    def power_density_w_per_kg(self, max_discharge_rate_c: float = 3.0) -> float:
        if self.mass_kg <= 0:
            return 0.0
        current = self.nominal_capacity_ah * max_discharge_rate_c
        power = current * self.nominal_voltage_v
        return round(power / self.mass_kg, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "gravimetric_wh_per_kg": self.gravimetric_energy_density_wh_per_kg(),
            "volumetric_wh_per_l": self.volumetric_energy_density_wh_per_l(),
            "power_density_w_per_kg": self.power_density_w_per_kg(),
        }

    def run(self):
        print("=" * 60)
        print("ENERGY DENSITY CALCULATOR")
        print("=" * 60)
        ed = EnergyDensity(
            mass_kg=0.05, volume_liters=0.025,
            nominal_capacity_ah=5.0, nominal_voltage_v=3.7
        )
        print(f"Mass: {ed.mass_kg} kg, Volume: {ed.volume_liters} L")
        print(f"Gravimetric: {ed.gravimetric_energy_density_wh_per_kg():.2f} Wh/kg")
        print(f"Volumetric: {ed.volumetric_energy_density_wh_per_l():.2f} Wh/L")
        print(f"Mass per kWh: {ed.mass_energy_ratio_kg_per_kwh():.3f} kg/kWh")
        print(f"Volume per kWh: {ed.volume_per_kwh_liters():.3f} L/kWh")
        print(f"Power density: {ed.power_density_w_per_kg():.2f} W/kg")
        print(f"Stats: {ed.stats()}")

if __name__ == "__main__":
    EnergyDensity(0, 0, 0, 0).run()
