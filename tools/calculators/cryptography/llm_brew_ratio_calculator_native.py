"""Native stdlib module: Brew Ratio Calculator
Calculates coffee-to-water ratios, strength, and dilution.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class BrewRatioCalculator:
    coffee_dose_g: float
    brew_water_g: float
    desired_tds_pct: Optional[float] = None

    def ratio_1_to_x(self) -> float:
        if self.coffee_dose_g == 0:
            return 0
        return self.brew_water_g / self.coffee_dose_g

    def ratio_pct(self) -> float:
        total = self.coffee_dose_g + self.brew_water_g
        if total == 0:
            return 0
        return (self.coffee_dose_g / total) * 100

    def estimated_tds_pct(self) -> float:
        ratio = self.ratio_1_to_x()
        if ratio == 0:
            return 0
        return 1.8 / (ratio ** 0.5)

    def estimated_ey_pct(self) -> float:
        tds = self.estimated_tds_pct()
        if self.coffee_dose_g == 0:
            return 0
        return (self.brew_water_g * tds / 100 / self.coffee_dose_g) * 100

    def water_to_add_for_tds(self, target_tds_pct: float) -> float:
        current_tds = self.estimated_tds_pct()
        if current_tds == 0:
            return 0
        total_solids = self.coffee_dose_g * (current_tds / 100)
        target_total_beverage = total_solids / (target_tds_pct / 100)
        return target_total_beverage - self.brew_water_g

    def ratio_category(self) -> str:
        r = self.ratio_1_to_x()
        if r < 13:
            return "ristretto_style"
        elif r < 16:
            return "standard_espresso"
        elif r < 18:
            return "lungo"
        elif r < 20:
            return "strong_drip"
        elif r < 25:
            return "standard_drip"
        return "weak_drip"

    def stats(self, target_tds_pct: Optional[float] = None) -> Dict:
        result = {
            "coffee_dose_g": self.coffee_dose_g,
            "brew_water_g": self.brew_water_g,
            "ratio_1_to_x": round(self.ratio_1_to_x(), 1),
            "ratio_pct": round(self.ratio_pct(), 2),
            "estimated_tds_pct": round(self.estimated_tds_pct(), 2),
            "estimated_ey_pct": round(self.estimated_ey_pct(), 2),
            "ratio_category": self.ratio_category(),
        }
        if target_tds_pct is not None:
            result["water_to_add_for_tds_ml"] = round(self.water_to_add_for_tds(target_tds_pct), 1)
        return result

def run():
    brc = BrewRatioCalculator(coffee_dose_g=20, brew_water_g=340)
    print(brc.stats(target_tds_pct=1.25))

if __name__ == "__main__":
    run()
