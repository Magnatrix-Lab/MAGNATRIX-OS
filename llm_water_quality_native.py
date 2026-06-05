"""Water Quality -- turbidity, pH, dissolved oxygen, coliform, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class WaterQuality:
    ph: float = 7.0
    turbidity_ntu: float = 1.0
    dissolved_oxygen_mg_l: float = 8.0
    total_coliform_mpn: float = 0.0
    temperature_c: float = 20.0

    def ph_status(self) -> str:
        if 6.5 <= self.ph <= 8.5: return "acceptable"
        elif 6.0 <= self.ph < 6.5 or 8.5 < self.ph <= 9.0: return "marginal"
        return "unacceptable"

    def turbidity_status(self) -> str:
        if self.turbidity_ntu <= 1: return "excellent"
        elif self.turbidity_ntu <= 4: return "acceptable"
        elif self.turbidity_ntu <= 10: return "marginal"
        return "unacceptable"

    def do_status(self) -> str:
        if self.dissolved_oxygen_mg_l >= 6: return "good"
        elif self.dissolved_oxygen_mg_l >= 4: return "moderate"
        return "poor"

    def safe_for_drinking(self) -> bool:
        return (self.ph_status() == "acceptable" and 
                self.turbidity_ntu <= 4 and 
                self.total_coliform_mpn == 0 and 
                self.dissolved_oxygen_mg_l >= 4)

    def wqi(self) -> float:
        scores = [
            max(0, 100 - abs(self.ph - 7.5) * 20),
            max(0, 100 - self.turbidity_ntu * 10),
            min(100, self.dissolved_oxygen_mg_l * 12.5),
            100 if self.total_coliform_mpn == 0 else max(0, 100 - self.total_coliform_mpn * 10)
        ]
        return sum(scores) / len(scores)

    def stats(self) -> Dict:
        return {"ph": self.ph_status(), "turbidity": self.turbidity_status(), "do": self.do_status(), "safe": self.safe_for_drinking(), "wqi": round(self.wqi(), 1)}

def run():
    wq = WaterQuality(ph=7.2, turbidity_ntu=2, dissolved_oxygen_mg_l=7.5, total_coliform_mpn=0)
    print(wq.stats())

if __name__ == "__main__":
    run()
