"""Visual Acuity Converter — Snellen, LogMAR, decimal, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class VisualAcuityConverter:
    snellen: str = "6/6"

    def to_decimal(self) -> float:
        parts = self.snellen.split("/")
        if len(parts) == 2:
            try:
                return float(parts[0]) / float(parts[1])
            except:
                return 1.0
        return 1.0

    def to_logmar(self) -> float:
        d = self.to_decimal()
        return -math.log10(d) if d > 0 else 0.0

    def from_logmar(self, logmar: float) -> str:
        d = 10 ** (-logmar)
        if d >= 1.0:
            return f"6/{int(6/d)}"
        return f"6/{int(6/d)}"

    def from_decimal(self, decimal: float) -> str:
        if decimal > 0:
            return f"6/{int(6/decimal)}"
        return "6/60"

    def is_legal_blind(self, better_eye: str = "6/60") -> bool:
        d = self.to_decimal()
        better = VisualAcuityConverter(better_eye).to_decimal()
        return d < 0.1 or better < 0.1

    def category(self) -> str:
        d = self.to_decimal()
        if d >= 1.0: return "normal"
        elif d >= 0.5: return "mild impairment"
        elif d >= 0.2: return "moderate impairment"
        elif d >= 0.05: return "severe impairment"
        return "blind"

    def stats(self) -> Dict:
        return {"snellen": self.snellen, "decimal": round(self.to_decimal(), 3), "logmar": round(self.to_logmar(), 2), "category": self.category()}

def run():
    for s in ["6/6", "6/12", "6/60", "3/60"]:
        vac = VisualAcuityConverter(s)
        print(vac.stats())

if __name__ == "__main__":
    run()
