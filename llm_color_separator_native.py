"""Color Separator -- CMYK, spot, halftone, trapping, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class ColorSeparator:
    rgb: Tuple[int, int, int] = (0, 0, 0)

    def to_cmyk(self) -> Tuple[float, float, float, float]:
        r, g, b = self.rgb[0] / 255, self.rgb[1] / 255, self.rgb[2] / 255
        k = 1 - max(r, g, b)
        c = (1 - r - k) / (1 - k) if k < 1 else 0
        m = (1 - g - k) / (1 - k) if k < 1 else 0
        y = (1 - b - k) / (1 - k) if k < 1 else 0
        return round(c, 3), round(m, 3), round(y, 3), round(k, 3)

    def total_ink_coverage(self) -> float:
        c, m, y, k = self.to_cmyk()
        return (c + m + y + k) * 100

    def halftone_dots(self, lpi: int = 150) -> int:
        return lpi ** 2

    def trapping_offset(self, base_color: str) -> float:
        if base_color in ["cyan", "magenta", "yellow"]:
            return 0.1
        return 0.2

    def spot_color_needed(self, brand_colors: List[Tuple[int, int, int]]) -> bool:
        for bc in brand_colors:
            if bc != self.rgb:
                return True
        return False

    def stats(self) -> Dict:
        return {"rgb": self.rgb, "cmyk": self.to_cmyk(), "ink_coverage": round(self.total_ink_coverage(), 1)}

def run():
    cs = ColorSeparator((255, 128, 0))
    print(cs.stats())

if __name__ == "__main__":
    run()
