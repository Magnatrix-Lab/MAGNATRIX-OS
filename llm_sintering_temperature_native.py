"""Sintering Temperature Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class SinteringTemperature:
    material: str
    particle_size_um: float
    green_density_percent: float = 60.0
    heating_rate_c_per_min: float = 5.0

    def melting_point_c(self) -> float:
        points = {"steel": 1538, "alumina": 2072, "titanium": 1668, "wc": 2870, "zirconia": 2715, "silicon": 1414}
        return points.get(self.material, 1500)

    def sintering_temperature_c(self) -> float:
        return round(self.melting_point_c() * 0.75, 1)

    def hold_time_min(self) -> float:
        factor = 1 + (100 - self.green_density_percent) / 20.0
        return round(30 * factor, 1)

    def total_cycle_time_min(self, max_temp_c: float = None) -> float:
        if max_temp_c is None:
            max_temp_c = self.sintering_temperature_c()
        heating = (max_temp_c - 25) / self.heating_rate_c_per_min
        cooling = heating * 0.5
        return round(heating + self.hold_time_min() + cooling, 1)

    def shrinkage_percent(self) -> float:
        return round((100 - self.green_density_percent) * 0.8, 1)

    def final_density_percent(self) -> float:
        return round(self.green_density_percent + self.shrinkage_percent(), 1)

    def energy_kwh(self, part_weight_kg: float = 1.0, furnace_capacity_kg: float = 10.0) -> float:
        specific = 0.5
        energy = part_weight_kg * specific * (self.sintering_temperature_c() - 25) / 3600
        return round(energy * (furnace_capacity_kg / max(part_weight_kg, 0.1)), 2)

    def stats(self) -> Dict[str, float]:
        return {
            "sintering_temperature_c": self.sintering_temperature_c(),
            "hold_time_min": self.hold_time_min(),
            "shrinkage_percent": self.shrinkage_percent(),
        }

    def run(self):
        print("=" * 60)
        print("SINTERING TEMPERATURE CALCULATOR")
        print("=" * 60)
        st = SinteringTemperature(
            material="steel", particle_size_um=10, green_density_percent=60, heating_rate_c_per_min=5
        )
        print(f"Material: {st.material}")
        print(f"Melting point: {st.melting_point_c()} C")
        print(f"Sintering temp: {st.sintering_temperature_c():.1f} C")
        print(f"Hold time: {st.hold_time_min():.1f} min")
        print(f"Total cycle: {st.total_cycle_time_min():.1f} min")
        print(f"Shrinkage: {st.shrinkage_percent():.1f}%")
        print(f"Final density: {st.final_density_percent():.1f}%")
        print(f"Stats: {st.stats()}")

if __name__ == "__main__":
    SinteringTemperature("steel", 0).run()
