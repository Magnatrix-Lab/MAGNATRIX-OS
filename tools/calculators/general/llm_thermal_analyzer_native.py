"""Thermal Analyzer — heat transfer, insulation, U-value, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class ThermalAnalyzer:
    area_m2: float = 50.0
    u_value: float = 1.5
    temp_diff: float = 15.0

    def heat_loss(self) -> float:
        return self.area_m2 * self.u_value * self.temp_diff

    def insulation_savings(self, new_u: float = 0.3) -> float:
        return self.area_m2 * (self.u_value - new_u) * self.temp_diff

    def payback_years(self, insulation_cost: float = 500.0, energy_cost_per_kwh: float = 0.15) -> float:
        annual_hours = 2000.0
        savings_kwh = self.insulation_savings() * annual_hours / 1000.0
        annual_savings = savings_kwh * energy_cost_per_kwh
        return insulation_cost / annual_savings if annual_savings > 0 else 0.0

    def stats(self) -> Dict:
        return {"heat_loss_w": round(self.heat_loss(), 2), "savings_w": round(self.insulation_savings(), 2), "payback_years": round(self.payback_years(), 2)}

def run():
    ta = ThermalAnalyzer(area_m2=80, u_value=2.0, temp_diff=20)
    print(ta.stats())

if __name__ == "__main__":
    run()
