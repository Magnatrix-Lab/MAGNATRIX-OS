"""Native stdlib module: SO2 Calculator
Calculates free SO2, total SO2, and molecular SO2 for wine preservation.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class SO2Calculator:
    free_so2_mg_l: float
    total_so2_mg_l: float
    ph: float

    def bound_so2_mg_l(self) -> float:
        return self.total_so2_mg_l - self.free_so2_mg_l

    def molecular_so2_mg_l(self) -> float:
        if self.ph == 0:
            return 0.0
        return self.free_so2_mg_l / (1 + 10 ** (self.ph - 1.81))

    def molecular_so2_pct(self) -> float:
        if self.free_so2_mg_l == 0:
            return 0.0
        return (self.molecular_so2_mg_l() / self.free_so2_mg_l()) * 100

    def antimicrobial_protection(self) -> str:
        mol = self.molecular_so2_mg_l()
        if mol >= 0.8:
            return "strong"
        elif mol >= 0.5:
            return "moderate"
        elif mol >= 0.3:
            return "weak"
        return "insufficient"

    def recommended_addition_mg_l(self, target_free_so2: float) -> float:
        return max(0, target_free_so2 - self.free_so2_mg_l)

    def stats(self) -> Dict:
        return {
            "free_so2_mg_l": self.free_so2_mg_l,
            "total_so2_mg_l": self.total_so2_mg_l,
            "bound_so2_mg_l": round(self.bound_so2_mg_l(), 1),
            "molecular_so2_mg_l": round(self.molecular_so2_mg_l(), 3),
            "molecular_so2_pct": round(self.molecular_so2_pct(), 3),
            "protection": self.antimicrobial_protection(),
        }

def run():
    so2 = SO2Calculator(free_so2_mg_l=30, total_so2_mg_l=120, ph=3.4)
    print(so2.stats())

if __name__ == "__main__":
    run()
