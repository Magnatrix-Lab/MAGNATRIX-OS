"""Native stdlib module: Ink Coverage Calculator
Calculates ink usage, coverage per letter, and refill needs.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class InkCoverageCalculator:
    text_length_chars: int
    nib_size_mm: float = 2.0
    line_spacing_multiplier: float = 2.0
    ink_type: str = "waterbased"  # waterbased, pigmented, iron_gall

    _INK_PER_CM = {
        "waterbased": 0.015,
        "pigmented": 0.012,
        "iron_gall": 0.010,
    }

    def ink_per_char_ml(self) -> float:
        base = self._INK_PER_CM.get(self.ink_type, 0.015)
        return base * (self.nib_size_mm / 2.0)

    def total_ink_ml(self) -> float:
        return self.text_length_chars * self.ink_per_char_ml()

    def pages_needed(self, lines_per_page: int = 20, chars_per_line: int = 50) -> int:
        if lines_per_page == 0 or chars_per_line == 0:
            return 0
        total_chars_per_page = lines_per_page * chars_per_line
        return (self.text_length_chars + total_chars_per_page - 1) // total_chars_per_page

    def bottle_refills_needed(self, bottle_size_ml: float = 30.0) -> int:
        if bottle_size_ml == 0:
            return 0
        return (self.total_ink_ml() + bottle_size_ml - 1) // bottle_size_ml

    def cost_estimate(self, cost_per_ml: float = 0.5) -> float:
        return self.total_ink_ml() * cost_per_ml

    def stats(self, lines_per_page: int = 20, chars_per_line: int = 50, bottle_size_ml: float = 30.0) -> Dict:
        return {
            "text_length_chars": self.text_length_chars,
            "ink_type": self.ink_type,
            "total_ink_ml": round(self.total_ink_ml(), 2),
            "pages_needed": self.pages_needed(lines_per_page, chars_per_line),
            "bottle_refills": self.bottle_refills_needed(bottle_size_ml),
            "cost_estimate_usd": round(self.cost_estimate(), 2),
        }

def run():
    icc = InkCoverageCalculator(text_length_chars=5000, nib_size_mm=1.5, ink_type="pigmented")
    print(icc.stats())

if __name__ == "__main__":
    run()
