"""Heat Treatment Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class HeatTreatment:
    metal_type: str
    part_weight_kg: float
    part_surface_area_m2: float
    treatment_type: str = "annealing"
    target_temp_c: float = 800.0

    def heating_time_min(self) -> float:
        thickness = math.sqrt(self.part_weight_kg / (self.part_surface_area_m2 * 8000)) * 1000
        rates = {"annealing": 2.0, "quenching": 1.0, "tempering": 1.5, "normalizing": 2.0}
        rate = rates.get(self.treatment_type, 2.0)
        return round(thickness * rate, 1)

    def holding_time_min(self) -> float:
        holds = {"annealing": 60, "quenching": 5, "tempering": 120, "normalizing": 30, "carburizing": 240}
        return holds.get(self.treatment_type, 60)

    def cooling_time_min(self) -> float:
        coolings = {"annealing": 120, "quenching": 2, "tempering": 60, "normalizing": 60, "carburizing": 180}
        return coolings.get(self.treatment_type, 120)

    def total_cycle_time_min(self) -> float:
        return round(self.heating_time_min() + self.holding_time_min() + self.cooling_time_min(), 1)

    def energy_kwh(self) -> float:
        specific_heat = 0.5
        return round(self.part_weight_kg * specific_heat * (self.target_temp_c - 25) / 3600, 2)

    def furnace_load_kg_per_m2(self) -> float:
        if self.part_surface_area_m2 <= 0:
            return 0.0
        return round(self.part_weight_kg / self.part_surface_area_m2, 2)

    def hardness_after_hrc(self) -> float:
        if self.treatment_type == "quenching":
            return 55.0
        elif self.treatment_type == "tempering":
            return 40.0
        elif self.treatment_type == "annealing":
            return 20.0
        else:
            return 30.0

    def stats(self) -> Dict[str, float]:
        return {
            "total_cycle_time_min": self.total_cycle_time_min(),
            "energy_kwh": self.energy_kwh(),
            "hardness_after_hrc": self.hardness_after_hrc(),
        }

    def run(self):
        print("=" * 60)
        print("HEAT TREATMENT CALCULATOR")
        print("=" * 60)
        ht = HeatTreatment(
            metal_type="steel", part_weight_kg=50, part_surface_area_m2=0.5,
            treatment_type="quenching", target_temp_c=850
        )
        print(f"Metal: {ht.metal_type}, Treatment: {ht.treatment_type}")
        print(f"Heating: {ht.heating_time_min():.1f} min")
        print(f"Holding: {ht.holding_time_min()} min")
        print(f"Cooling: {ht.cooling_time_min()} min")
        print(f"Total cycle: {ht.total_cycle_time_min():.1f} min")
        print(f"Energy: {ht.energy_kwh():.2f} kWh")
        print(f"Hardness: {ht.hardness_after_hrc():.1f} HRC")
        print(f"Stats: {ht.stats()}")

if __name__ == "__main__":
    HeatTreatment("steel", 0, 0).run()
