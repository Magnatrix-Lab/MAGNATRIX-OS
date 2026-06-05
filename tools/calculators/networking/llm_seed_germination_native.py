"""Seed Germination Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class SeedGermination:
    seeds_planted: int
    seeds_germinated: int
    germination_temp_c: float = 25.0
    soil_moisture_percent: float = 60.0

    def germination_rate_percent(self) -> float:
        if self.seeds_planted <= 0:
            return 0.0
        return round(self.seeds_germinated / self.seeds_planted * 100, 2)

    def expected_germination(self, seed_viability_percent: float = 90.0) -> int:
        return int(self.seeds_planted * seed_viability_percent / 100.0)

    def germination_speed_index(self, days_to_germinate: float = 7.0) -> float:
        if days_to_germinate <= 0:
            return 0.0
        rate = self.germination_rate_percent()
        return round(rate / days_to_germinate, 2)

    def temperature_stress_factor(self, optimal_temp_c: float = 25.0) -> float:
        return max(0.5, 1 - abs(self.germination_temp_c - optimal_temp_c) / 15.0)

    def moisture_stress_factor(self, optimal_moisture: float = 60.0) -> float:
        return max(0.5, 1 - abs(self.soil_moisture_percent - optimal_moisture) / 40.0)

    def adjusted_germination_rate(self, seed_viability_percent: float = 90.0) -> float:
        base = self.germination_rate_percent()
        temp = self.temperature_stress_factor()
        moisture = self.moisture_stress_factor()
        return round(base * temp * moisture, 2)

    def seeding_rate_kg_per_ha(self, seed_weight_g: float = 0.05,
                                  target_plants_per_ha: float = 100000) -> float:
        rate = self.germination_rate_percent() / 100.0
        if rate <= 0:
            return 0.0
        return round(target_plants_per_ha * seed_weight_g / 1000.0 / rate, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "germination_rate_percent": self.germination_rate_percent(),
            "temperature_stress": self.temperature_stress_factor(),
            "moisture_stress": self.moisture_stress_factor(),
        }

    def run(self):
        print("=" * 60)
        print("SEED GERMINATION CALCULATOR")
        print("=" * 60)
        sg = SeedGermination(
            seeds_planted=200, seeds_germinated=170,
            germination_temp_c=22, soil_moisture_percent=55
        )
        print(f"Planted: {sg.seeds_planted}, Germinated: {sg.seeds_germinated}")
        print(f"Rate: {sg.germination_rate_percent():.2f}%")
        print(f"Expected: {sg.expected_germination()}")
        print(f"Speed index: {sg.germination_speed_index():.2f}")
        print(f"Temp stress: {sg.temperature_stress_factor():.2f}")
        print(f"Moisture stress: {sg.moisture_stress_factor():.2f}")
        print(f"Adjusted rate: {sg.adjusted_germination_rate():.2f}%")
        print(f"Stats: {sg.stats()}")

if __name__ == "__main__":
    SeedGermination(0, 0).run()
