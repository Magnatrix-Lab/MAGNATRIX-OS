"""Typography Analyzer — line height, measure, hierarchy, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class TypographyAnalyzer:
    font_size_pt: float = 12.0
    line_length_char: int = 66

    def optimal_line_height(self) -> float:
        return self.font_size_pt * 1.5

    def measure_in_mm(self) -> float:
        return self.font_size_pt * 0.3528 * self.line_length_char

    def scale_ratio(self, h1_size: float = 48.0) -> float:
        return h1_size / self.font_size_pt if self.font_size_pt > 0 else 0.0

    def stats(self) -> Dict:
        return {"line_height_pt": round(self.optimal_line_height(), 2), "measure_mm": round(self.measure_in_mm(), 1), "h1_ratio": round(self.scale_ratio(), 2)}

def run():
    ta = TypographyAnalyzer(font_size_pt=14, line_length_char=72)
    print(ta.stats())

if __name__ == "__main__":
    run()
