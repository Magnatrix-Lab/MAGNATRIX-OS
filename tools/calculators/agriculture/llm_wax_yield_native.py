"""Native stdlib module: Wax Yield Calculator
Estimates beeswax production from honey harvest and cappings.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class WaxYieldCalculator:
    honey_harvested_kg: float
    cappings_wax_pct: float = 2.0
    comb_replacement_kg: float = 0.0
    wax_per_frame_g: float = 80
    frames_replaced: int = 0

    def cappings_wax_kg(self) -> float:
        return self.honey_harvested_kg * (self.cappings_wax_pct / 100)

    def comb_wax_kg(self) -> float:
        return self.comb_replacement_kg + (self.frames_replaced * self.wax_per_frame_g / 1000)

    def total_wax_kg(self) -> float:
        return self.cappings_wax_kg() + self.comb_wax_kg()

    def revenue(self, wax_price_per_kg: float) -> float:
        return self.total_wax_kg() * wax_price_per_kg

    def stats(self, wax_price_per_kg: float = 0) -> Dict:
        return {
            "honey_harvested_kg": self.honey_harvested_kg,
            "cappings_wax_kg": round(self.cappings_wax_kg(), 2),
            "comb_wax_kg": round(self.comb_wax_kg(), 2),
            "total_wax_kg": round(self.total_wax_kg(), 2),
            "revenue": round(self.revenue(wax_price_per_kg), 2) if wax_price_per_kg else None,
        }

def run():
    wy = WaxYieldCalculator(honey_harvested_kg=500, cappings_wax_pct=2.0, comb_replacement_kg=1.5, frames_replaced=20, wax_per_frame_g=80)
    print(wy.stats(wax_price_per_kg=25))

if __name__ == "__main__":
    run()
