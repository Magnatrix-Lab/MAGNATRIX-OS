"""Battery Cycle Life Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class BatteryCycleLife:
    chemistry: str
    depth_of_discharge_percent: float = 80.0
    charge_rate_c: float = 1.0
    temperature_c: float = 25.0
    target_capacity_fade_percent: float = 20.0

    def baseline_cycles(self) -> int:
        cycles = {"li_ion": 1000, "lifepo4": 3000, "lead_acid": 500, "nimh": 800, "nicd": 1000, "lto": 10000}
        return cycles.get(self.chemistry, 1000)

    def dod_factor(self) -> float:
        dod = self.depth_of_discharge_percent / 100.0
        return round(1 / (dod ** 1.5), 3)

    def temperature_factor(self) -> float:
        if self.temperature_c <= 25:
            return 1.0
        return round(math.exp((25 - self.temperature_c) / 8.0), 3)

    def charge_rate_factor(self) -> float:
        if self.charge_rate_c <= 1.0:
            return 1.0
        return round(math.exp((1.0 - self.charge_rate_c) / 2.0), 3)

    def estimated_cycles(self) -> int:
        base = self.baseline_cycles()
        dod = self.depth_of_discharge_percent / 100.0
        factor = 1.0
        if dod < 1.0:
            factor *= 1 / (dod ** 1.3)
        factor *= self.temperature_factor()
        factor *= self.charge_rate_factor()
        return int(base * factor)

    def cycle_life_years(self, cycles_per_year: int = 365) -> float:
        cycles = self.estimated_cycles()
        if cycles_per_year <= 0:
            return 0.0
        return round(cycles / cycles_per_year, 1)

    def capacity_after_cycles(self, cycles: int) -> float:
        total_cycles = self.estimated_cycles()
        if total_cycles <= 0:
            return 0.0
        fade = self.target_capacity_fade_percent / 100.0
        remaining = 1 - fade * (cycles / total_cycles)
        return round(max(remaining, 0.5) * 100, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "estimated_cycles": self.estimated_cycles(),
            "cycle_life_years": self.cycle_life_years(),
            "dod_factor": self.dod_factor(),
        }

    def run(self):
        print("=" * 60)
        print("BATTERY CYCLE LIFE CALCULATOR")
        print("=" * 60)
        life = BatteryCycleLife(
            chemistry="lifepo4", depth_of_discharge_percent=90,
            charge_rate_c=1.5, temperature_c=30, target_capacity_fade_percent=20
        )
        print(f"Chemistry: {life.chemistry}")
        print(f"Baseline cycles: {life.baseline_cycles()}")
        print(f"DOD: {life.depth_of_discharge_percent}%")
        print(f"Estimated cycles: {life.estimated_cycles()}")
        print(f"Cycle life: {life.cycle_life_years():.1f} years")
        print(f"Capacity after 1000 cycles: {life.capacity_after_cycles(1000):.2f}%")
        print(f"Stats: {life.stats()}")

if __name__ == "__main__":
    BatteryCycleLife("li_ion").run()
