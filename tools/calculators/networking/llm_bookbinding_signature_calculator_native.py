"""Native stdlib module: Bookbinding Signature Calculator
Calculates signatures, page counts, imposition, and sheet needs.
"""
from dataclasses import dataclass
from typing import Dict, Optional
import math

@dataclass
class BookbindingSignatureCalculator:
    total_pages: int
    pages_per_sheet: int = 4
    sheets_per_signature: int = 4

    def pages_per_signature(self) -> int:
        return self.pages_per_sheet * self.sheets_per_signature

    def total_signatures(self) -> int:
        if self.pages_per_signature() == 0:
            return 0
        return math.ceil(self.total_pages / self.pages_per_signature())

    def total_sheets(self) -> int:
        return self.total_signatures() * self.sheets_per_signature

    def leftover_pages(self) -> int:
        if self.pages_per_signature() == 0:
            return 0
        return self.pages_per_signature() - (self.total_pages % self.pages_per_signature())

    def spine_thickness_mm(self, paper_thickness_mm: float = 0.1) -> float:
        return self.total_sheets() * paper_thickness_mm

    def stats(self, paper_thickness_mm: float = 0.1) -> Dict:
        return {
            "total_pages": self.total_pages,
            "pages_per_signature": self.pages_per_signature(),
            "total_signatures": self.total_signatures(),
            "total_sheets": self.total_sheets(),
            "leftover_pages": self.leftover_pages(),
            "spine_thickness_mm": round(self.spine_thickness_mm(paper_thickness_mm), 1),
        }

def run():
    bsc = BookbindingSignatureCalculator(total_pages=128, pages_per_sheet=4, sheets_per_signature=4)
    print(bsc.stats())

if __name__ == "__main__":
    run()
