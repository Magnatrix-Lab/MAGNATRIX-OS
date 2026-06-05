"""Native stdlib module: Candle Wax Calculator
Calculates wax needed, wick sizing, and fragrance load for candles.
"""
from dataclasses import dataclass
from typing import Dict, Optional
import math

@dataclass
class CandleWaxCalculator:
    container_volume_ml: float
    wax_type: str  # soy, paraffin, beeswax, coconut, palm
    fragrance_load_pct: float = 6.0
    wick_type: str = "cotton"

    _WAX_DENSITIES = {"soy": 0.93, "paraffin": 0.90, "beeswax": 0.95, "coconut": 0.92, "palm": 0.88}
    _WAX_MELT_POOL_MULT = {"soy": 1.1, "paraffin": 1.0, "beeswax": 1.2, "coconut": 1.15, "palm": 1.05}

    def wax_weight_g(self) -> float:
        density = self._WAX_DENSITIES.get(self.wax_type, 0.9)
        return self.container_volume_ml * density

    def fragrance_weight_g(self) -> float:
        return self.wax_weight_g() * (self.fragrance_load_pct / 100)

    def total_batch_weight_g(self) -> float:
        return self.wax_weight_g() + self.fragrance_weight_g()

    def wick_size_recommended(self) -> str:
        vol = self.container_volume_ml
        if vol < 100:
            return "small (CD-8 / ECO-6)"
        elif vol < 200:
            return "medium (CD-12 / ECO-10)"
        elif vol < 350:
            return "large (CD-16 / ECO-14)"
        return "extra_large (CD-22 / ECO-18)"

    def melt_pool_diameter_mm(self) -> float:
        mult = self._WAX_MELT_POOL_MULT.get(self.wax_type, 1.0)
        return (self.container_volume_ml * 0.1) ** 0.5 * 20 * mult

    def recommended_cure_days(self) -> int:
        cures = {"soy": 14, "paraffin": 3, "beeswax": 7, "coconut": 14, "palm": 7}
        return cures.get(self.wax_type, 7)

    def stats(self) -> Dict:
        return {
            "wax_weight_g": round(self.wax_weight_g(), 1),
            "fragrance_weight_g": round(self.fragrance_weight_g(), 2),
            "total_batch_weight_g": round(self.total_batch_weight_g(), 1),
            "wick_size": self.wick_size_recommended(),
            "melt_pool_diameter_mm": round(self.melt_pool_diameter_mm(), 1),
            "recommended_cure_days": self.recommended_cure_days(),
        }

def run():
    cwc = CandleWaxCalculator(container_volume_ml=250, wax_type="soy", fragrance_load_pct=8)
    print(cwc.stats())

if __name__ == "__main__":
    run()
