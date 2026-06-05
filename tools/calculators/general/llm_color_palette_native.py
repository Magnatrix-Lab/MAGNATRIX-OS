"""Color Palette Generator — complementary, triadic, analogous, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class ColorPaletteGenerator:
    base_hue: float = 200.0

    def complementary(self) -> List[float]:
        return [self.base_hue, (self.base_hue + 180.0) % 360.0]

    def triadic(self) -> List[float]:
        return [self.base_hue, (self.base_hue + 120.0) % 360.0, (self.base_hue + 240.0) % 360.0]

    def analogous(self) -> List[float]:
        return [(self.base_hue - 30.0) % 360.0, self.base_hue, (self.base_hue + 30.0) % 360.0]

    def split_complementary(self) -> List[float]:
        return [self.base_hue, (self.base_hue + 150.0) % 360.0, (self.base_hue + 210.0) % 360.0]

    def stats(self) -> Dict:
        return {"complementary": self.complementary(), "triadic": self.triadic(), "analogous": self.analogous()}

def run():
    cpg = ColorPaletteGenerator(base_hue=45)
    print(cpg.stats())

if __name__ == "__main__":
    run()
