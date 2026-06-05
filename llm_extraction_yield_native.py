"""Extraction Yield — TDS, EY, strength, brew ratio, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class ExtractionYield:
    coffee_dose_g: float = 18.0
    beverage_weight_g: float = 36.0
    tds_pct: float = 8.0

    def extraction_yield_pct(self) -> float:
        if self.coffee_dose_g <= 0:
            return 0.0
        return self.beverage_weight_g * self.tds_pct / self.coffee_dose_g

    def brew_ratio(self) -> float:
        return self.beverage_weight_g / self.coffee_dose_g if self.coffee_dose_g > 0 else 0.0

    def strength(self) -> float:
        return self.tds_pct / 100

    def ideal_range(self) -> bool:
        ey = self.extraction_yield_pct()
        return 18 <= ey <= 22

    def under_over(self) -> str:
        ey = self.extraction_yield_pct()
        if ey < 18: return "under"
        elif ey > 22: return "over"
        return "ideal"

    def stats(self) -> Dict:
        return {"ey": round(self.extraction_yield_pct(), 2), "ratio": round(self.brew_ratio(), 2), "status": self.under_over()}

def run():
    ey = ExtractionYield(coffee_dose_g=20, beverage_weight_g=40, tds_pct=9.5)
    print(ey.stats())

if __name__ == "__main__":
    run()
