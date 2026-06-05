"""Native stdlib module: Paper Weight Calculator
Converts between GSM, thickness, bulk, and sheet weights.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class PaperWeightCalculator:
    gsm: float
    sheet_width_mm: float = 210.0
    sheet_height_mm: float = 297.0

    def sheet_area_m2(self) -> float:
        return (self.sheet_width_mm * self.sheet_height_mm) / 1_000_000

    def sheet_weight_g(self) -> float:
        return self.gsm * self.sheet_area_m2()

    def ream_weight_kg(self, sheets_per_ream: int = 500) -> float:
        return self.sheet_weight_g() * sheets_per_ream / 1000

    def bulk(self, thickness_mm: float) -> float:
        if self.gsm == 0:
            return 0
        return thickness_mm / self.gsm * 1000

    def thickness_mm(self, bulk_factor: float = 1.0) -> float:
        return self.gsm * bulk_factor / 1000

    def cover_equivalent(self) -> str:
        if self.gsm < 120:
            return "text"
        elif self.gsm < 200:
            return "light_cover"
        elif self.gsm < 300:
            return "cover"
        return "heavy_cover"

    def stats(self, thickness_mm: Optional[float] = None) -> Dict:
        result = {
            "gsm": self.gsm,
            "sheet_weight_g": round(self.sheet_weight_g(), 2),
            "ream_weight_kg": round(self.ream_weight_kg(), 2),
            "cover_equivalent": self.cover_equivalent(),
        }
        if thickness_mm is not None:
            result["bulk"] = round(self.bulk(thickness_mm), 2)
        else:
            result["estimated_thickness_mm"] = round(self.thickness_mm(), 3)
        return result

def run():
    pwc = PaperWeightCalculator(gsm=300, sheet_width_mm=210, sheet_height_mm=297)
    print(pwc.stats(thickness_mm=0.45))

if __name__ == "__main__":
    run()
