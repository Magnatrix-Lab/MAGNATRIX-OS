"""Native stdlib module: Coffee Extraction Calculator
Calculates TDS, extraction yield, and EY% for brewed coffee.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class CoffeeExtractionCalculator:
    coffee_dose_g: float
    brew_water_g: float
    beverage_weight_g: float
    tds_pct: float

    def extraction_yield_pct(self) -> float:
        if self.coffee_dose_g == 0:
            return 0
        return (self.beverage_weight_g * (self.tds_pct / 100) / self.coffee_dose_g) * 100

    def brew_ratio(self) -> float:
        if self.coffee_dose_g == 0:
            return 0
        return self.brew_water_g / self.coffee_dose_g

    def strength_pct(self) -> float:
        return self.tds_pct

    def water_retention_g(self) -> float:
        return self.brew_water_g - self.beverage_weight_g

    def absorption_ratio(self) -> float:
        if self.coffee_dose_g == 0:
            return 0
        return self.water_retention_g() / self.coffee_dose_g

    def extraction_quality(self) -> str:
        ey = self.extraction_yield_pct()
        if ey < 18:
            return "under_extracted"
        elif ey <= 22:
            return "ideal"
        elif ey <= 24:
            return "slightly_over"
        return "over_extracted"

    def strength_quality(self) -> str:
        if self.tds_pct < 1.15:
            return "weak"
        elif self.tds_pct <= 1.45:
            return "standard"
        elif self.tds_pct <= 1.65:
            return "strong"
        return "very_strong"

    def stats(self) -> Dict:
        return {
            "coffee_dose_g": self.coffee_dose_g,
            "brew_water_g": self.brew_water_g,
            "beverage_weight_g": self.beverage_weight_g,
            "tds_pct": self.tds_pct,
            "extraction_yield_pct": round(self.extraction_yield_pct(), 2),
            "brew_ratio": round(self.brew_ratio(), 1),
            "water_retention_g": round(self.water_retention_g(), 1),
            "absorption_ratio": round(self.absorption_ratio(), 2),
            "extraction_quality": self.extraction_quality(),
            "strength_quality": self.strength_quality(),
        }

def run():
    cec = CoffeeExtractionCalculator(coffee_dose_g=18, brew_water_g=300, beverage_weight_g=270, tds_pct=1.35)
    print(cec.stats())

if __name__ == "__main__":
    run()
