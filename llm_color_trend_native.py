"""Color Trend Analyzer — season palette, popularity, harmony, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class ColorTrendAnalyzer:
    colors: List[Dict] = field(default_factory=list)

    def dominant(self) -> Optional[str]:
        if not self.colors:
            return None
        return max(self.colors, key=lambda c: c.get("popularity", 0)).get("name")

    def rgb_distance(self, rgb1: List[int], rgb2: List[int]) -> float:
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)))

    def harmony_score(self, base_rgb: List[int] = None) -> float:
        if not self.colors or not base_rgb:
            return 0.0
        return sum(1.0 / (1.0 + self.rgb_distance(c.get("rgb", [0, 0, 0]), base_rgb)) for c in self.colors) / len(self.colors)

    def stats(self) -> Dict:
        return {"dominant": self.dominant(), "harmony": round(self.harmony_score([128, 128, 128]), 3)}

def run():
    cta = ColorTrendAnalyzer(colors=[{"name": "Sage", "popularity": 85, "rgb": [138, 154, 91]}, {"name": "Terracotta", "popularity": 72, "rgb": [204, 78, 92]}])
    print(cta.stats())

if __name__ == "__main__":
    run()
