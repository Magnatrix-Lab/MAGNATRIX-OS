"""Native stdlib module: Paper Caliper Calculator
Calculates paper thickness, bulk, and grammage relationships.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class PaperGrade(Enum):
    NEWSPRINT = "newsprint"
    BOOK = "book"
    COATED = "coated"
    LWC = "lwc"
    BOARD = "board"
    TISSUE = "tissue"

@dataclass
class PaperCaliperCalculator:
    paper_grade: PaperGrade
    grammage_g_m2: float
    caliper_um: float
    sheet_count: int = 1
    sheet_area_m2: float = 1.0

    def bulk_cm3_g(self) -> float:
        if self.grammage_g_m2 == 0:
            return 0.0
        return (self.caliper_um / 10000) / (self.grammage_g_m2 / 10000)

    def density_g_cm3(self) -> float:
        if self.caliper_um == 0:
            return 0.0
        return (self.grammage_g_m2 / 10000) / (self.caliper_um / 1e6)

    def total_thickness_mm(self) -> float:
        return (self.caliper_um * self.sheet_count) / 1000

    def total_weight_g(self) -> float:
        return self.grammage_g_m2 * self.sheet_area_m2 * self.sheet_count

    def pages_per_inch(self) -> float:
        if self.caliper_um == 0:
            return 0.0
        return 25400 / self.caliper_um

    def typical_caliper_for_grade(self) -> float:
        calipers = {PaperGrade.NEWSPRINT: 80, PaperGrade.BOOK: 100, PaperGrade.COATED: 90, PaperGrade.LWC: 75, PaperGrade.BOARD: 500, PaperGrade.TISSUE: 40}
        return calipers.get(self.paper_grade, 100)

    def stats(self) -> Dict:
        return {
            "paper_grade": self.paper_grade.value,
            "grammage_g_m2": self.grammage_g_m2,
            "caliper_um": self.caliper_um,
            "bulk_cm3_g": round(self.bulk_cm3_g(), 3),
            "density_g_cm3": round(self.density_g_cm3(), 3),
            "total_thickness_mm": round(self.total_thickness_mm(), 2),
            "total_weight_g": round(self.total_weight_g(), 1),
            "pages_per_inch": round(self.pages_per_inch(), 1),
        }

def run():
    pcc = PaperCaliperCalculator(paper_grade=PaperGrade.BOOK, grammage_g_m2=80, caliper_um=100, sheet_count=500, sheet_area_m2=0.0625)
    print(pcc.stats())

if __name__ == "__main__":
    run()
