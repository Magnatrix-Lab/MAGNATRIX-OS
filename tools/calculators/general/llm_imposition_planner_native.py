"""Imposition Planner -- signature, creep, fold, cut, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class ImpositionPlanner:
    pages: int = 32
    sheet_size: str = "A2"
    page_size: str = "A5"
    binding: str = "saddle"

    def pages_per_sheet(self) -> int:
        sizes = {("A2", "A5"): 8, ("A1", "A5"): 16, ("A2", "A4"): 4, ("A1", "A4"): 8}
        return sizes.get((self.sheet_size, self.page_size), 8)

    def sheets_needed(self) -> int:
        return math.ceil(self.pages / self.pages_per_sheet())

    def signatures(self) -> int:
        if self.binding == "saddle":
            return self.sheets_needed()
        return 1

    def creep_mm(self, paper_thickness_mm: float = 0.1) -> float:
        innermost_pages = self.pages_per_sheet() // 2
        return (innermost_pages - 1) * paper_thickness_mm * 2

    def page_order(self) -> List[int]:
        pps = self.pages_per_sheet()
        n = self.pages
        order = []
        for i in range(0, n, pps):
            block = list(range(i + 1, min(i + pps + 1, n + 1)))
            if len(block) < pps:
                block += [0] * (pps - len(block))
            order.extend(block)
        return order

    def stats(self) -> Dict:
        return {"pages_per_sheet": self.pages_per_sheet(), "sheets": self.sheets_needed(), "signatures": self.signatures(), "creep": self.creep_mm()}

def run():
    ip = ImpositionPlanner(64, "A2", "A5", "saddle")
    print(ip.stats())

if __name__ == "__main__":
    run()
