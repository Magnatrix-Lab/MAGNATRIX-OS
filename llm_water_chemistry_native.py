"""Water Chemistry — hardness, alkalinity, TDS, coffee extraction, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class WaterChemistry:
    calcium_mg_l: float = 50.0
    magnesium_mg_l: float = 10.0
    bicarbonate_mg_l: float = 100.0
    total_dissolved_solids: float = 200.0

    def total_hardness(self) -> float:
        return self.calcium_mg_l * 2.5 + self.magnesium_mg_l * 4.1

    def alkalinity(self) -> float:
        return self.bicarbonate_mg_l / 61 * 50

    def hardness_alkalinity_ratio(self) -> float:
        a = self.alkalinity()
        return self.total_hardness() / a if a > 0 else 0.0

    def sca_recommendation(self) -> str:
        h = self.total_hardness()
        if 50 <= h <= 175 and 40 <= self.alkalinity() <= 75:
            return "ideal"
        elif h < 50:
            return "too soft"
        elif h > 250:
            return "too hard"
        return "acceptable"

    def langelier_index(self, temp_c: float = 25) -> float:
        ph_s = 9.3 + math.log10(self.calcium_mg_l / 40) + math.log10(self.alkalinity() / 50)
        return 7.5 - ph_s

    def stats(self) -> Dict:
        return {"hardness": round(self.total_hardness(), 1), "alkalinity": round(self.alkalinity(), 1), "ratio": round(self.hardness_alkalinity_ratio(), 2), "sca": self.sca_recommendation()}

def run():
    import math
    wc = WaterChemistry(calcium_mg_l=80, magnesium_mg_l=20, bicarbonate_mg_l=150)
    print(wc.stats())

if __name__ == "__main__":
    run()
