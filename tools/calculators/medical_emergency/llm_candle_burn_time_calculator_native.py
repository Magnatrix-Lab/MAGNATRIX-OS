"""Native stdlib module: Candle Burn Time Calculator
Estimates burn duration, consumption rate, and performance metrics.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class CandleBurnTimeCalculator:
    wax_weight_g: float
    wax_type: str
    wick_burn_rate_g_per_hour: float = 0.5
    fragrance_load_pct: float = 6.0

    _WAX_BURN_RATES = {"soy": 0.06, "paraffin": 0.08, "beeswax": 0.05, "coconut": 0.055, "palm": 0.07}

    def wax_burn_rate_g_per_hour(self) -> float:
        return self._WAX_BURN_RATES.get(self.wax_type, 0.06)

    def estimated_burn_hours(self) -> float:
        return self.wax_weight_g / self.wax_burn_rate_g_per_hour()

    def consumption_rate_g_per_hour(self) -> float:
        return self.wax_burn_rate_g_per_hour() + self.wick_burn_rate_g_per_hour

    def burn_time_with_fragrance(self) -> float:
        factor = 1 - (self.fragrance_load_pct / 100) * 0.3
        return self.estimated_burn_hours() * factor

    def cost_per_hour(self, candle_cost: float) -> float:
        if self.burn_time_with_fragrance() == 0:
            return 0
        return candle_cost / self.burn_time_with_fragrance()

    def recommended_first_burn_hours(self, diameter_mm: float = 75) -> float:
        return max(1, diameter_mm / 25)

    def tunneling_risk(self, wick_size_match: str = "good") -> str:
        if wick_size_match == "too_small":
            return "high"
        elif wick_size_match == "good":
            return "low"
        return "moderate"

    def stats(self, candle_cost: float = 20.0, diameter_mm: float = 75) -> Dict:
        return {
            "estimated_burn_hours": round(self.estimated_burn_hours(), 1),
            "burn_time_with_fragrance": round(self.burn_time_with_fragrance(), 1),
            "consumption_rate_g_h": round(self.consumption_rate_g_per_hour(), 2),
            "cost_per_hour_usd": round(self.cost_per_hour(candle_cost), 2),
            "recommended_first_burn_hours": round(self.recommended_first_burn_hours(diameter_mm), 1),
            "wax_burn_rate_g_h": round(self.wax_burn_rate_g_per_hour(), 3),
        }

def run():
    cbtc = CandleBurnTimeCalculator(wax_weight_g=200, wax_type="soy", fragrance_load_pct=8)
    print(cbtc.stats())

if __name__ == "__main__":
    run()
