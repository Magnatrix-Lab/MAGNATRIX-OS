"""Milk Production Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class MilkProduction:
    cow_count: int
    avg_daily_yield_liters: float
    lactation_days: int = 305
    somatic_cell_count: float = 200000.0

    def total_annual_yield_liters(self) -> float:
        return round(self.cow_count * self.avg_daily_yield_liters * self.lactation_days, 1)

    def total_annual_yield_tons(self) -> float:
        return round(self.total_annual_yield_liters() / 1000.0, 2)

    def solids_production_kg(self, fat_percent: float = 4.0,
                              protein_percent: float = 3.3) -> float:
        total = self.total_annual_yield_liters()
        solids = fat_percent + protein_percent
        return round(total * solids / 100.0, 2)

    def fat_kg(self, fat_percent: float = 4.0) -> float:
        return round(self.total_annual_yield_liters() * fat_percent / 100.0, 2)

    def protein_kg(self, protein_percent: float = 3.3) -> float:
        return round(self.total_annual_yield_liters() * protein_percent / 100.0, 2)

    def revenue(self, price_per_liter: float = 0.4) -> float:
        return round(self.total_annual_yield_liters() * price_per_liter, 2)

    def milk_quality_index(self) -> float:
        scc = self.somatic_cell_count
        if scc < 100000:
            return 100.0
        elif scc < 200000:
            return 90.0
        elif scc < 400000:
            return 75.0
        else:
            return 50.0

    def stats(self) -> Dict[str, float]:
        return {
            "total_annual_yield_liters": self.total_annual_yield_liters(),
            "total_annual_yield_tons": self.total_annual_yield_tons(),
            "milk_quality_index": self.milk_quality_index(),
        }

    def run(self):
        print("=" * 60)
        print("MILK PRODUCTION CALCULATOR")
        print("=" * 60)
        mp = MilkProduction(
            cow_count=50, avg_daily_yield_liters=25, lactation_days=305, somatic_cell_count=150000
        )
        print(f"Cows: {mp.cow_count}")
        print(f"Daily yield: {mp.avg_daily_yield_liters} L")
        print(f"Annual yield: {mp.total_annual_yield_liters():.1f} L ({mp.total_annual_yield_tons():.2f} tons)")
        print(f"Fat: {mp.fat_kg():.2f} kg, Protein: {mp.protein_kg():.2f} kg")
        print(f"Revenue: ${mp.revenue():.2f}")
        print(f"Quality index: {mp.milk_quality_index():.2f}")
        print(f"Stats: {mp.stats()}")

if __name__ == "__main__":
    MilkProduction(0, 0).run()
