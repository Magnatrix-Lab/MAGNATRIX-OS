"""Seed Germinator — viability, dormancy, scarification, stratification, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class SeedGerminator:
    viability_pct: float = 85.0
    dormancy_type: str = "none"
    moisture_pct: float = 50.0
    temp_c: float = 25.0

    def germination_rate(self) -> float:
        base = self.viability_pct / 100
        if self.dormancy_type == "physical":
            base *= 0.3
        elif self.dormancy_type == "physiological":
            base *= 0.5
        if self.moisture_pct < 30:
            base *= 0.6
        if self.temp_c < 5 or self.temp_c > 40:
            base *= 0.1
        return base

    def stratification_needed(self) -> bool:
        return self.dormancy_type == "physiological"

    def scarification_needed(self) -> bool:
        return self.dormancy_type == "physical"

    def days_to_germinate(self, base_days: int = 7) -> int:
        rate = self.germination_rate()
        if rate <= 0:
            return float('inf')
        return int(base_days / rate)

    def stats(self) -> Dict:
        return {"germination_rate": round(self.germination_rate(), 3), "stratify": self.stratification_needed(), "scarify": self.scarification_needed()}

def run():
    sg = SeedGerminator(viability_pct=90, dormancy_type="physical", moisture_pct=40, temp_c=20)
    print(sg.stats())
    print("Days to germ:", sg.days_to_germinate())

if __name__ == "__main__":
    run()
