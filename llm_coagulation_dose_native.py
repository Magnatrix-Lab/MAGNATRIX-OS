"""Coagulation Dose Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class CoagulationDose:
    water_flow_m3_h: float
    turbidity_ntu: float
    coagulant_type: str = "alum"
    target_turbidity_ntu: float = 5.0
    ph: float = 7.0

    def base_dose_mg_l(self) -> float:
        doses = {"alum": 5, "ferric_chloride": 4, "pac": 3, "polymer": 1}
        return doses.get(self.coagulant_type, 5)

    def turbidity_factor(self) -> float:
        return max(0.5, self.turbidity_ntu / 50.0)

    def ph_factor(self) -> float:
        optimal = {"alum": 6.5, "ferric_chloride": 7.0, "pac": 7.0, "polymer": 7.0}
        opt = optimal.get(self.coagulant_type, 7.0)
        return max(0.5, 1.0 - abs(self.ph - opt) / 3.0)

    def required_dose_mg_l(self) -> float:
        return round(self.base_dose_mg_l() * self.turbidity_factor() * self.ph_factor(), 2)

    def daily_dose_kg(self) -> float:
        return round(self.required_dose_mg_l() * self.water_flow_m3_h * 24 / 1000.0, 2)

    def sludge_production_kg_per_day(self) -> float:
        return round(self.daily_dose_kg() * 1.5 + self.water_flow_m3_h * 24 * self.turbidity_ntu / 1000.0 * 0.1, 2)

    def cost_per_day(self, price_per_kg: float = 1.5) -> float:
        return round(self.daily_dose_kg() * price_per_kg, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "required_dose_mg_l": self.required_dose_mg_l(),
            "daily_dose_kg": self.daily_dose_kg(),
            "sludge_kg_per_day": self.sludge_production_kg_per_day(),
        }

    def run(self):
        print("=" * 60)
        print("COAGULATION DOSE CALCULATOR")
        print("=" * 60)
        coag = CoagulationDose(
            water_flow_m3_h=100, turbidity_ntu=150,
            coagulant_type="alum", target_turbidity_ntu=5, ph=6.8
        )
        print(f"Flow: {coag.water_flow_m3_h} m3/h")
        print(f"Turbidity: {coag.turbidity_ntu} NTU")
        print(f"Coagulant: {coag.coagulant_type}")
        print(f"Required dose: {coag.required_dose_mg_l():.2f} mg/L")
        print(f"Daily dose: {coag.daily_dose_kg():.2f} kg")
        print(f"Sludge: {coag.sludge_production_kg_per_day():.2f} kg/day")
        print(f"Cost: ${coag.cost_per_day():.2f}/day")
        print(f"Stats: {coag.stats()}")

if __name__ == "__main__":
    CoagulationDose(0, 0).run()
