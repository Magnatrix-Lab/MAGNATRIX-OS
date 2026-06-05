"""Wastewater BOD Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class WastewaterBOD:
    initial_do_mg_l: float
    final_do_mg_l: float
    sample_volume_ml: float
    dilution_factor: float = 1.0
    seed_correction_mg_l: float = 0.0

    def bod5_mg_l(self) -> float:
        do_depletion = self.initial_do_mg_l - self.final_do_mg_l - self.seed_correction_mg_l
        if do_depletion <= 0:
            return 0.0
        return round(do_depletion * self.dilution_factor, 2)

    def cod_estimate_mg_l(self) -> float:
        return round(self.bod5_mg_l() * 2.5, 2)

    def bod_removal_efficiency(self, influent_bod_mg_l: float) -> float:
        if influent_bod_mg_l <= 0:
            return 0.0
        eff = 1 - self.bod5_mg_l() / influent_bod_mg_l
        return round(max(eff, 0) * 100, 2)

    def oxygen_uptake_rate_mg_l_h(self, incubation_days: float = 5.0) -> float:
        if incubation_days <= 0:
            return 0.0
        return round(self.bod5_mg_l() / (incubation_days * 24), 3)

    def population_equivalent(self, per_capita_bod_g_day: float = 60.0) -> float:
        if per_capita_bod_g_day <= 0:
            return 0.0
        return round(self.bod5_mg_l() * 1000 / per_capita_bod_g_day, 1)

    def stats(self) -> Dict[str, float]:
        return {
            "bod5_mg_l": self.bod5_mg_l(),
            "cod_estimate_mg_l": self.cod_estimate_mg_l(),
            "oxygen_uptake_rate_mg_l_h": self.oxygen_uptake_rate_mg_l_h(),
        }

    def run(self):
        print("=" * 60)
        print("WASTEWATER BOD CALCULATOR")
        print("=" * 60)
        bod = WastewaterBOD(
            initial_do_mg_l=8.5, final_do_mg_l=3.2,
            sample_volume_ml=300, dilution_factor=2.0, seed_correction_mg_l=0.1
        )
        print(f"Initial DO: {bod.initial_do_mg_l} mg/L")
        print(f"Final DO: {bod.final_do_mg_l} mg/L")
        print(f"BOD5: {bod.bod5_mg_l():.2f} mg/L")
        print(f"COD estimate: {bod.cod_estimate_mg_l():.2f} mg/L")
        print(f"Removal efficiency: {bod.bod_removal_efficiency(200):.2f}%")
        print(f"Oxygen uptake: {bod.oxygen_uptake_rate_mg_l_h():.3f} mg/L/h")
        print(f"Population equivalent: {bod.population_equivalent():.1f} PE")
        print(f"Stats: {bod.stats()}")

if __name__ == "__main__":
    WastewaterBOD(0, 0, 0).run()
