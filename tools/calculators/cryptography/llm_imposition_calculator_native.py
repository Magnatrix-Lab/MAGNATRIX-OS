"""Native stdlib module: Imposition Calculator
Calculates sheet usage, signatures, and press sheet layouts for printing.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class ImpositionCalculator:
    job_name: str
    page_count: int
    pages_per_sheet: int
    sheet_size: str
    signatures: int = 1

    def sheets_needed(self) -> int:
        if self.pages_per_sheet == 0:
            return 0
        return math.ceil(self.page_count / self.pages_per_sheet)

    def waste_sheets(self, spoilage_pct: float = 5.0) -> int:
        return math.ceil(self.sheets_needed() * (spoilage_pct / 100))

    def total_sheets(self, spoilage_pct: float = 5.0) -> int:
        return self.sheets_needed() + self.waste_sheets(spoilage_pct)

    def pages_per_signature(self) -> int:
        if self.signatures == 0:
            return 0
        return math.ceil(self.page_count / self.signatures)

    def stats(self, spoilage_pct: float = 5.0) -> Dict:
        return {
            "job": self.job_name,
            "page_count": self.page_count,
            "pages_per_sheet": self.pages_per_sheet,
            "sheets_needed": self.sheets_needed(),
            "waste_sheets": self.waste_sheets(spoilage_pct),
            "total_sheets": self.total_sheets(spoilage_pct),
            "signatures": self.signatures,
        }

def run():
    ic = ImpositionCalculator(job_name="Booklet", page_count=32, pages_per_sheet=8, sheet_size="11x17", signatures=2)
    print(ic.stats())

if __name__ == "__main__":
    run()
