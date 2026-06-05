"""Shelf Life Estimator — Arrhenius, Q10, expiration, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class ShelfLifeEstimator:
    reference_temp: float = 25.0
    reference_life: float = 365.0
    q10: float = 2.0
    activation_energy: float = 83.14

    def life_at_temp(self, temp: float) -> float:
        return self.reference_life / (self.q10 ** ((temp - self.reference_temp) / 10))

    def arrhenius_life(self, temp: float, k_ref: float = 1.0) -> float:
        R = 8.314
        t_k = temp + 273.15
        t_ref_k = self.reference_temp + 273.15
        k = k_ref * math.exp(-self.activation_energy / R * (1/t_k - 1/t_ref_k))
        return self.reference_life * (k_ref / k) if k > 0 else 0.0

    def remaining_life(self, stored_temp: float, days_stored: float) -> float:
        total = self.life_at_temp(stored_temp)
        return max(0, total - days_stored)

    def quality_loss(self, temp: float, time: float) -> float:
        life = self.life_at_temp(temp)
        return min(1.0, time / life) if life > 0 else 1.0

    def stats(self, temp: float) -> Dict:
        return {"life_at_temp": round(self.life_at_temp(temp), 1), "arrhenius": round(self.arrhenius_life(temp), 1)}

def run():
    sle = ShelfLifeEstimator()
    print(sle.stats(35))
    print("Remaining:", sle.remaining_life(35, 100))
    print("Quality loss:", sle.quality_loss(35, 100))

if __name__ == "__main__":
    run()
