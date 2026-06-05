"""Native stdlib module: Type Scale Calculator
Calculates modular type scales, hierarchy ratios, and font sizes.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
import math

@dataclass
class TypeScaleCalculator:
    base_size_pt: float = 16.0
    scale_ratio: float = 1.25
    steps: int = 6

    def scale_sizes(self) -> List[float]:
        sizes = []
        for i in range(-2, self.steps + 1):
            sizes.append(round(self.base_size_pt * (self.scale_ratio ** i), 2))
        return sizes

    def size_at_step(self, step: int) -> float:
        return round(self.base_size_pt * (self.scale_ratio ** step), 2)

    def line_height_for_size(self, size_pt: float, ratio: float = 1.5) -> float:
        return round(size_pt * ratio, 1)

    def margin_top_em(self, size_pt: float) -> float:
        return round(size_pt / self.base_size_pt, 2)

    def contrast_ratio(self, size_a: float, size_b: float) -> float:
        if size_a == 0 or size_b == 0:
            return 0
        return round(max(size_a, size_b) / min(size_a, size_b), 2)

    def hierarchy_levels(self) -> List[Dict]:
        levels = []
        names = ["caption", "small", "base", "h6", "h5", "h4", "h3", "h2", "h1"]
        sizes = self.scale_sizes()
        for name, size in zip(names, sizes):
            levels.append({
                "name": name,
                "size_pt": size,
                "line_height_pt": self.line_height_for_size(size),
                "margin_top_em": self.margin_top_em(size),
            })
        return levels

    def stats(self) -> Dict:
        return {
            "base_size_pt": self.base_size_pt,
            "scale_ratio": self.scale_ratio,
            "hierarchy": self.hierarchy_levels(),
            "contrast_base_to_h1": self.contrast_ratio(self.base_size_pt, self.size_at_step(self.steps)),
        }

def run():
    tsc = TypeScaleCalculator(base_size_pt=16, scale_ratio=1.333, steps=6)
    print(tsc.stats())

if __name__ == "__main__":
    run()
