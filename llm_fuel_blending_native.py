"""Fuel Blending Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class FuelBlendComponent:
    name: str
    volume_fraction: float
    octane: float
    density_kg_m3: float
    energy_mj_per_kg: float

@dataclass
class FuelBlending:
    components: List[FuelBlendComponent]
    total_volume_liters: float

    def blend_property(self, getter) -> float:
        total = 0.0
        for c in self.components:
            total += c.volume_fraction * getter(c)
        return round(total, 2)

    def blend_octane(self) -> float:
        return self.blend_property(lambda c: c.octane)

    def blend_density_kg_m3(self) -> float:
        return self.blend_property(lambda c: c.density_kg_m3)

    def blend_energy_mj_per_kg(self) -> float:
        return self.blend_property(lambda c: c.energy_mj_per_kg)

    def total_energy_mj(self) -> float:
        mass_kg = self.total_volume_liters * self.blend_density_kg_m3() / 1000.0
        return round(mass_kg * self.blend_energy_mj_per_kg(), 2)

    def total_mass_kg(self) -> float:
        return round(self.total_volume_liters * self.blend_density_kg_m3() / 1000.0, 2)

    def cost_per_liter(self, component_costs: Dict[str, float]) -> float:
        cost = 0.0
        for c in self.components:
            cost += c.volume_fraction * component_costs.get(c.name, 0.0)
        return round(cost, 3)

    def stats(self) -> Dict[str, float]:
        return {
            "blend_octane": self.blend_octane(),
            "blend_density_kg_m3": self.blend_density_kg_m3(),
            "total_energy_mj": self.total_energy_mj(),
        }

    def run(self):
        print("=" * 60)
        print("FUEL BLENDING CALCULATOR")
        print("=" * 60)
        comps = [
            FuelBlendComponent("gasoline", 0.85, 95, 750, 44),
            FuelBlendComponent("ethanol", 0.15, 109, 789, 27),
        ]
        blend = FuelBlending(comps, total_volume_liters=1000)
        print(f"Components: {[c.name for c in blend.components]}")
        print(f"Blend octane: {blend.blend_octane():.2f}")
        print(f"Blend density: {blend.blend_density_kg_m3():.2f} kg/m3")
        print(f"Blend energy: {blend.blend_energy_mj_per_kg():.2f} MJ/kg")
        print(f"Total mass: {blend.total_mass_kg():.2f} kg")
        print(f"Total energy: {blend.total_energy_mj():.2f} MJ")
        print(f"Stats: {blend.stats()}")

if __name__ == "__main__":
    FuelBlending([], 0).run()
