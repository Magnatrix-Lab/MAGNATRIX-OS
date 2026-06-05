"""Metal Melting Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class MetalMelting:
    metal_type: str
    mass_kg: float
    initial_temp_c: float = 25.0
    superheat_c: float = 100.0

    def melting_point_c(self) -> float:
        points = {"iron": 1538, "aluminum": 660, "copper": 1085, "steel": 1510, "gold": 1064, "silver": 962, "lead": 328, "tin": 232}
        return points.get(self.metal_type, 1500)

    def specific_heat_kj_per_kg_k(self) -> float:
        heats = {"iron": 0.45, "aluminum": 0.9, "copper": 0.385, "steel": 0.42, "gold": 0.129, "silver": 0.235, "lead": 0.13, "tin": 0.23}
        return heats.get(self.metal_type, 0.45)

    def latent_heat_kj_per_kg(self) -> float:
        latent = {"iron": 272, "aluminum": 397, "copper": 209, "steel": 272, "gold": 63, "silver": 105, "lead": 23, "tin": 59}
        return latent.get(self.metal_type, 272)

    def heat_to_melting_kj(self) -> float:
        sh = self.specific_heat_kj_per_kg_k()
        return round(self.mass_kg * sh * (self.melting_point_c() - self.initial_temp_c), 2)

    def heat_for_melting_kj(self) -> float:
        return round(self.mass_kg * self.latent_heat_kj_per_kg(), 2)

    def heat_for_superheat_kj(self) -> float:
        sh = self.specific_heat_kj_per_kg_k()
        return round(self.mass_kg * sh * self.superheat_c, 2)

    def total_heat_required_kj(self) -> float:
        return round(self.heat_to_melting_kj() + self.heat_for_melting_kj() + self.heat_for_superheat_kj(), 2)

    def energy_kwh(self) -> float:
        return round(self.total_heat_required_kj() / 3600, 2)

    def furnace_time_minutes(self, furnace_power_kw: float = 100.0) -> float:
        if furnace_power_kw <= 0:
            return 0.0
        efficiency = 0.7
        return round(self.energy_kwh() / (furnace_power_kw * efficiency / 60.0), 1)

    def stats(self) -> Dict[str, float]:
        return {
            "melting_point_c": self.melting_point_c(),
            "total_heat_kj": self.total_heat_required_kj(),
            "energy_kwh": self.energy_kwh(),
        }

    def run(self):
        print("=" * 60)
        print("METAL MELTING CALCULATOR")
        print("=" * 60)
        mm = MetalMelting(
            metal_type="aluminum", mass_kg=500, initial_temp_c=25, superheat_c=100
        )
        print(f"Metal: {mm.metal_type}")
        print(f"Melting point: {mm.melting_point_c()} C")
        print(f"Heat to melting: {mm.heat_to_melting_kj():.2f} kJ")
        print(f"Heat for melting: {mm.heat_for_melting_kj():.2f} kJ")
        print(f"Heat for superheat: {mm.heat_for_superheat_kj():.2f} kJ")
        print(f"Total heat: {mm.total_heat_required_kj():.2f} kJ")
        print(f"Energy: {mm.energy_kwh():.2f} kWh")
        print(f"Furnace time (100kW): {mm.furnace_time_minutes():.1f} min")
        print(f"Stats: {mm.stats()}")

if __name__ == "__main__":
    MetalMelting("iron", 0).run()
