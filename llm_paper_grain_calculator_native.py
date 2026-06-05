"""Native stdlib module: Paper Grain Calculator
Calculates grain direction, folding benefits, and sheet layouts.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class PaperGrainCalculator:
    sheet_width_mm: float
    sheet_height_mm: float
    grain_direction: str  # long or short
    paper_weight_gsm: float = 80.0

    def fold_with_grain(self) -> bool:
        return self.grain_direction == "long"

    def fold_resistance_score(self) -> float:
        if self.fold_with_grain():
            return 100 - self.paper_weight_gsm * 0.2
        return 100 - self.paper_weight_gsm * 0.5

    def pages_per_sheet(self, page_width_mm: float, page_height_mm: float) -> int:
        if self.sheet_width_mm == 0 or self.sheet_height_mm == 0:
            return 0
        across = int(self.sheet_width_mm / page_width_mm)
        down = int(self.sheet_height_mm / page_height_mm)
        return across * down

    def optimal_page_orientation(self, page_width_mm: float, page_height_mm: float) -> str:
        w = self.sheet_width_mm
        h = self.sheet_height_mm
        if w >= h:
            return "portrait" if page_width_mm <= page_height_mm else "landscape"
        return "landscape" if page_width_mm <= page_height_mm else "portrait"

    def stats(self, page_width_mm: float = 148, page_height_mm: float = 210) -> Dict:
        return {
            "sheet_width_mm": self.sheet_width_mm,
            "sheet_height_mm": self.sheet_height_mm,
            "grain_direction": self.grain_direction,
            "fold_with_grain": self.fold_with_grain(),
            "fold_resistance_score": round(self.fold_resistance_score(), 1),
            "pages_per_sheet": self.pages_per_sheet(page_width_mm, page_height_mm),
            "optimal_orientation": self.optimal_page_orientation(page_width_mm, page_height_mm),
        }

def run():
    pgc = PaperGrainCalculator(sheet_width_mm=420, sheet_height_mm=297, grain_direction="long", paper_weight_gsm=120)
    print(pgc.stats())

if __name__ == "__main__":
    run()
