"""Animal Vitals — HR, RR, temp, species norms, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class AnimalVitals:
    species: str = "dog"
    weight_kg: float = 20.0
    heart_rate: float = 0.0
    resp_rate: float = 0.0
    temp_c: float = 0.0

    def norms(self) -> Dict[str, Tuple[float, float]]:
        return {
            "dog": (60, 140, 10, 35, 38.0, 39.2),
            "cat": (140, 220, 20, 30, 38.0, 39.2),
            "horse": (28, 44, 8, 16, 37.5, 38.5),
            "cow": (48, 84, 10, 30, 38.0, 39.5),
        }

    def check_hr(self) -> str:
        n = self.norms().get(self.species, (60, 140, 10, 35, 38.0, 39.2))
        if self.heart_rate < n[0]: return "low"
        if self.heart_rate > n[1]: return "high"
        return "normal"

    def check_rr(self) -> str:
        n = self.norms().get(self.species, (60, 140, 10, 35, 38.0, 39.2))
        if self.resp_rate < n[2]: return "low"
        if self.resp_rate > n[3]: return "high"
        return "normal"

    def check_temp(self) -> str:
        n = self.norms().get(self.species, (60, 140, 10, 35, 38.0, 39.2))
        if self.temp_c < n[4]: return "low"
        if self.temp_c > n[5]: return "high"
        return "normal"

    def shock_index(self) -> float:
        return self.heart_rate / self.resp_rate if self.resp_rate > 0 else 0.0

    def stats(self) -> Dict:
        return {"hr": self.check_hr(), "rr": self.check_rr(), "temp": self.check_temp(), "shock_index": round(self.shock_index(), 2)}

def run():
    av = AnimalVitals("dog", 25, 160, 40, 39.5)
    print(av.stats())

if __name__ == "__main__":
    run()
