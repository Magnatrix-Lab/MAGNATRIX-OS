"""Native stdlib module: Wine Fermentation Calculator
Calculates Brix to alcohol conversion, fermentation rates, and residual sugar.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class WineFermentationCalculator:
    initial_brix: float
    current_brix: float
    volume_l: float
    yeast_strain: str = "ec1118"

    def alcohol_by_volume_pct(self) -> float:
        brix_consumed = self.initial_brix - self.current_brix
        return brix_consumed * 0.59

    def residual_sugar_g_l(self) -> float:
        return self.current_brix * 10

    def total_sugar_g(self) -> float:
        return self.initial_brix * 10 * self.volume_l

    def sugar_consumed_g(self) -> float:
        return (self.initial_brix - self.current_brix) * 10 * self.volume_l

    def fermentation_rate_brix_per_day(self, days_elapsed: float) -> float:
        if days_elapsed == 0:
            return 0.0
        return (self.initial_brix - self.current_brix) / days_elapsed

    def attenuation_pct(self) -> float:
        if self.initial_brix == 0:
            return 0.0
        return ((self.initial_brix - self.current_brix) / self.initial_brix) * 100

    def is_dry(self) -> bool:
        return self.current_brix < 1.0

    def stats(self, days_elapsed: float = 0) -> Dict:
        return {
            "initial_brix": self.initial_brix,
            "current_brix": self.current_brix,
            "abv_pct": round(self.alcohol_by_volume_pct(), 1),
            "residual_sugar_g_l": round(self.residual_sugar_g_l(), 1),
            "attenuation_pct": round(self.attenuation_pct(), 1),
            "fermentation_rate": round(self.fermentation_rate_brix_per_day(days_elapsed), 2) if days_elapsed else None,
            "is_dry": self.is_dry(),
        }

def run():
    wfc = WineFermentationCalculator(initial_brix=22, current_brix=2, volume_l=100)
    print(wfc.stats(days_elapsed=14))

if __name__ == "__main__":
    run()
