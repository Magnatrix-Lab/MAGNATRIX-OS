"""Native stdlib module: Spawn Rate Calculator
Calculates spawn rate, inoculation timing, and colonization schedules.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class SpawnRateCalculator:
    species: str
    substrate_weight_kg: float
    spawn_rate_pct: float
    spawn_cost_per_kg: float

    def spawn_needed_kg(self) -> float:
        return self.substrate_weight_kg * (self.spawn_rate_pct / 100)

    def spawn_cost(self) -> float:
        return self.spawn_needed_kg() * self.spawn_cost_per_kg

    def colonization_days(self) -> int:
        rates = {"oyster": 14, "shiitake": 21, "button": 10, "lion_mane": 18, "enoki": 12}
        return rates.get(self.species.lower(), 14)

    def incubation_temp_c(self) -> float:
        temps = {"oyster": 24, "shiitake": 23, "button": 22, "lion_mane": 22, "enoki": 20}
        return temps.get(self.species.lower(), 23)

    def stats(self) -> Dict:
        return {
            "species": self.species,
            "substrate_kg": self.substrate_weight_kg,
            "spawn_rate_pct": self.spawn_rate_pct,
            "spawn_needed_kg": round(self.spawn_needed_kg(), 1),
            "spawn_cost": round(self.spawn_cost(), 2),
            "colonization_days": self.colonization_days(),
            "incubation_temp_c": self.incubation_temp_c(),
        }

def run():
    sr = SpawnRateCalculator(species="Shiitake", substrate_weight_kg=100, spawn_rate_pct=5, spawn_cost_per_kg=8)
    print(sr.stats())

if __name__ == "__main__":
    run()
