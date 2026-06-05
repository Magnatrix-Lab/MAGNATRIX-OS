"""Native stdlib module: Paper Weight Calculator
Converts between paper weight systems and calculates sheet quantities.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class PaperWeightCalculator:
    gsm: float
    sheet_width_in: float
    sheet_height_in: float

    def lbs_per_1000_sheets(self) -> float:
        area_sqm = (self.sheet_width_in * 0.0254) * (self.sheet_height_in * 0.0254)
        return (self.gsm * area_sqm * 1000) / 453.592

    def lbs_per_ream(self) -> float:
        return self.lbs_per_1000_sheets() / 2

    def weight_per_sheet_g(self) -> float:
        area_sqm = (self.sheet_width_in * 0.0254) * (self.sheet_height_in * 0.0254)
        return self.gsm * area_sqm

    def sheets_per_kg(self) -> float:
        if self.weight_per_sheet_g() == 0:
            return 0.0
        return 1000 / self.weight_per_sheet_g()

    def stats(self) -> Dict[str, float]:
        return {
            "gsm": self.gsm,
            "lbs_per_1000": round(self.lbs_per_1000_sheets(), 2),
            "lbs_per_ream": round(self.lbs_per_ream(), 2),
            "weight_per_sheet_g": round(self.weight_per_sheet_g(), 3),
            "sheets_per_kg": round(self.sheets_per_kg(), 1),
        }

def run():
    pwc = PaperWeightCalculator(gsm=80, sheet_width_in=8.5, sheet_height_in=11)
    print(pwc.stats())

if __name__ == "__main__":
    run()
