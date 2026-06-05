"""IOP Calculator — tonometry, pachymetry, correction, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class IOPCalculator:
    measured_iop: float = 15.0
    cct_um: float = 550.0

    def corrected_iop(self, method: str = "ehlers") -> float:
        if method == "ehlers":
            return self.measured_iop + (self.cct_um - 520) / 10 * 0.5
        elif method == "shah":
            return self.measured_iop + (self.cct_um - 545) / 20 * 1.0
        return self.measured_iop

    def cct_percentile(self) -> str:
        if self.cct_um > 600: return "thick (>95th)"
        elif self.cct_um < 490: return "thin (<5th)"
        return "average"

    def risk_assessment(self, age: int = 50, family_history: bool = False) -> str:
        cor = self.corrected_iop()
        risk = 0
        if cor > 21: risk += 1
        if self.cct_um < 500: risk += 1
        if age > 60: risk += 1
        if family_history: risk += 1
        if risk >= 3: return "high"
        elif risk >= 2: return "moderate"
        return "low"

    def diurnal_variation(self, readings: List[float]) -> float:
        return max(readings) - min(readings) if readings else 0.0

    def stats(self) -> Dict:
        return {
            "measured": self.measured_iop,
            "corrected_ehlers": round(self.corrected_iop("ehlers"), 1),
            "corrected_shah": round(self.corrected_iop("shah"), 1),
            "cct_status": self.cct_percentile()
        }

def run():
    iop = IOPCalculator(measured_iop=18, cct_um=480)
    print(iop.stats())
    print("Risk:", iop.risk_assessment(age=65, family_history=True))

if __name__ == "__main__":
    run()
