"""Epoxy Curing Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class EpoxyCuring:
    resin_mass_g: float
    hardener_mass_g: float
    curing_temp_c: float = 25.0
    curing_time_hours: float = 24.0
    epoxy_type: str = "dg_eba"

    def mix_ratio_actual(self) -> float:
        if self.hardener_mass_g <= 0:
            return 0.0
        return round(self.resin_mass_g / self.hardener_mass_g, 2)

    def recommended_mix_ratio(self) -> float:
        ratios = {"dg_eba": 2.0, "dg_eba_fast": 1.5, "novolac": 0.8, "aliphatic": 1.0}
        return ratios.get(self.epoxy_type, 2.0)

    def ratio_accuracy(self) -> float:
        rec = self.recommended_mix_ratio()
        if rec <= 0:
            return 0.0
        return round(self.mix_ratio_actual() / rec * 100, 2)

    def cure_degree(self) -> float:
        base_rate = 0.02
        temp_factor = math.exp((self.curing_temp_c - 25) / 10.0)
        degree = 1 - math.exp(-base_rate * temp_factor * self.curing_time_hours)
        return round(min(degree, 1.0), 4)

    def gel_time_minutes(self) -> float:
        base_gel = 120
        temp_factor = max(0.2, math.exp((25 - self.curing_temp_c) / 8.0))
        ratio_factor = 1.0 + abs(self.mix_ratio_actual() - self.recommended_mix_ratio()) * 0.2
        return round(base_gel * temp_factor * ratio_factor, 1)

    def glass_transition_c(self) -> float:
        max_tg = 120
        return round(max_tg * self.cure_degree(), 1)

    def exotherm_peak_c(self) -> float:
        return round(self.curing_temp_c + 50 * self.cure_degree(), 1)

    def stats(self) -> Dict[str, float]:
        return {
            "cure_degree": self.cure_degree(),
            "glass_transition_c": self.glass_transition_c(),
            "gel_time_minutes": self.gel_time_minutes(),
        }

    def run(self):
        print("=" * 60)
        print("EPOXY CURING CALCULATOR")
        print("=" * 60)
        ep = EpoxyCuring(
            resin_mass_g=100, hardener_mass_g=50,
            curing_temp_c=60, curing_time_hours=4, epoxy_type="dg_eba"
        )
        print(f"Resin: {ep.resin_mass_g} g, Hardener: {ep.hardener_mass_g} g")
        print(f"Mix ratio: 1:{ep.mix_ratio_actual():.2f}")
        print(f"Recommended: 1:{ep.recommended_mix_ratio():.2f}")
        print(f"Ratio accuracy: {ep.ratio_accuracy():.2f}%")
        print(f"Cure degree: {ep.cure_degree():.4f}")
        print(f"Gel time: {ep.gel_time_minutes():.1f} min")
        print(f"Glass transition: {ep.glass_transition_c():.1f} C")
        print(f"Exotherm peak: {ep.exotherm_peak_c():.1f} C")
        print(f"Stats: {ep.stats()}")

if __name__ == "__main__":
    EpoxyCuring(0, 0).run()
