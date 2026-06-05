"""Logo Optimizer — legibility, contrast, scalability, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class LogoOptimizer:
    width_px: int = 512
    height_px: int = 512

    def min_size_legible(self) -> float:
        return max(self.width_px, self.height_px) / 32.0

    def contrast_ratio(self, lum1: float = 0.2126, lum2: float = 0.7152) -> float:
        return (lum1 + 0.05) / (lum2 + 0.05) if lum2 > lum1 else (lum2 + 0.05) / (lum1 + 0.05)

    def scale_factor(self, target_width: int = 128) -> float:
        return target_width / self.width_px if self.width_px > 0 else 0.0

    def stats(self) -> Dict:
        return {"min_legible_px": round(self.min_size_legible(), 1), "contrast": round(self.contrast_ratio(), 2), "scale_128": round(self.scale_factor(), 3)}

def run():
    lo = LogoOptimizer(width_px=1024, height_px=1024)
    print(lo.stats())

if __name__ == "__main__":
    run()
