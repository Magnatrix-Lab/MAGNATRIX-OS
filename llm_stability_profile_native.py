"""Stability Profile — degradation, shelf life, Arrhenius, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class StabilityProfile:
    initial_potency: float = 100.0
    current_potency: float = 95.0
    storage_temp: float = 25.0
    activation_energy: float = 83.0
    """kJ/mol"""

    def degradation_rate(self, time_months: float) -> float:
        if time_months <= 0:
            return 0.0
        return (self.initial_potency - self.current_potency) / time_months

    def shelf_life(self, limit: float = 90.0) -> float:
        rate = self.degradation_rate(12)
        if rate <= 0:
            return float('inf')
        return (self.initial_potency - limit) / rate

    def arrhenius_factor(self, temp_c: float, ref_temp: float = 25.0) -> float:
        R = 8.314
        T = temp_c + 273.15
        T_ref = ref_temp + 273.15
        return math.exp(-self.activation_energy * 1000 / R * (1/T - 1/T_ref))

    def accelerated_stability(self, temp_c: float, time_months: float) -> float:
        factor = self.arrhenius_factor(temp_c)
        return self.initial_potency - self.degradation_rate(time_months) * factor * time_months

    def q10_rule(self, q10: float = 2.0, delta_t: float = 10.0) -> float:
        return q10 ** (delta_t / 10)

    def stats(self) -> Dict:
        return {
            "degradation_rate_12mo": round(self.degradation_rate(12), 2),
            "shelf_life_months": round(self.shelf_life(), 1),
            "potency": self.current_potency
        }

def run():
    sp = StabilityProfile(initial_potency=100, current_potency=92, storage_temp=30, activation_energy=75)
    print(sp.stats())
    print("Arrhenius factor at 40°C:", sp.arrhenius_factor(40))
    print("Q10:", sp.q10_rule(2, 10))

if __name__ == "__main__":
    run()
