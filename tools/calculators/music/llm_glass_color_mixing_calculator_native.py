"""Native stdlib module: Glass Color Mixing Calculator
Calculates color mixing, frit percentages, and tint recipes.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class GlassColorMixingCalculator:
    base_glass_g: float
    colorant_pct: float

    def colorant_g(self) -> float:
        return self.base_glass_g * (self.colorant_pct / 100)

    def total_batch_g(self) -> float:
        return self.base_glass_g + self.colorant_g()

    def opacity_estimate(self) -> float:
        return min(100, self.colorant_pct * 5)

    def color_intensity(self) -> str:
        if self.colorant_pct < 0.5:
            return "very_pale"
        elif self.colorant_pct < 2:
            return "light"
        elif self.colorant_pct < 5:
            return "medium"
        elif self.colorant_pct < 10:
            return "strong"
        return "very_strong"

    def frit_needed_g(self, target_colorant_g: float) -> float:
        if self.colorant_pct == 0:
            return 0
        return target_colorant_g / (self.colorant_pct / 100)

    def stats(self, target_colorant_g: Optional[float] = None) -> Dict:
        result = {
            "base_glass_g": self.base_glass_g,
            "colorant_pct": self.colorant_pct,
            "colorant_g": round(self.colorant_g(), 2),
            "total_batch_g": round(self.total_batch_g(), 2),
            "opacity_estimate_pct": round(self.opacity_estimate(), 1),
            "color_intensity": self.color_intensity(),
        }
        if target_colorant_g is not None:
            result["frit_needed_g"] = round(self.frit_needed_g(target_colorant_g), 2)
        return result

def run():
    gcm = GlassColorMixingCalculator(base_glass_g=500, colorant_pct=2.5)
    print(gcm.stats(target_colorant_g=15))

if __name__ == "__main__":
    run()
