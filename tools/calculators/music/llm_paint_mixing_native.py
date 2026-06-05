"""Paint Mixing Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

@dataclass
class PaintMixing:
    base_color: str
    base_volume_liters: float
    target_color: str
    pigment_concentration_percent: float = 10.0
    additives: Dict[str, float] = field(default_factory=dict)

    def pigment_volume_liters(self) -> float:
        return round(self.base_volume_liters * self.pigment_concentration_percent / 100.0, 3)

    def thinner_ratio(self) -> float:
        ratios = {"matte": 0.15, "gloss": 0.10, "satin": 0.12, "primer": 0.20}
        return ratios.get(self.target_color.lower(), 0.15)

    def total_volume_liters(self) -> float:
        thinner = self.base_volume_liters * self.thinner_ratio()
        additive_vol = sum(self.additives.values())
        return round(self.base_volume_liters + thinner + additive_vol, 3)

    def mix_proportions(self) -> Dict[str, float]:
        total = self.total_volume_liters()
        if total <= 0:
            return {}
        thinner = self.base_volume_liters * self.thinner_ratio()
        result = {
            "base": round(self.base_volume_liters / total * 100, 2),
            "thinner": round(thinner / total * 100, 2),
            "pigment": round(self.pigment_volume_liters() / total * 100, 2),
        }
        for name, qty in self.additives.items():
            result[name] = round(qty / total * 100, 2)
        return result

    def coverage_sqm(self, coverage_rate: float = 10.0) -> float:
        total = self.total_volume_liters()
        return round(total * coverage_rate, 1)

    def stats(self) -> Dict[str, float]:
        return {
            "total_volume_liters": self.total_volume_liters(),
            "pigment_volume_liters": self.pigment_volume_liters(),
            "coverage_sqm": self.coverage_sqm(),
        }

    def run(self):
        print("=" * 60)
        print("PAINT MIXING CALCULATOR")
        print("=" * 60)
        paint = PaintMixing(
            base_color="white", base_volume_liters=5.0,
            target_color="navy blue", pigment_concentration_percent=12.0,
            additives={"anti_sagging": 0.1, "uv_stabilizer": 0.05}
        )
        print(f"Base: {paint.base_color}, {paint.base_volume_liters} L")
        print(f"Target: {paint.target_color}")
        print(f"Pigment volume: {paint.pigment_volume_liters():.3f} L")
        print(f"Thinner ratio: {paint.thinner_ratio():.2f}")
        print(f"Total volume: {paint.total_volume_liters():.3f} L")
        print(f"Mix proportions: {paint.mix_proportions()}")
        print(f"Coverage: {paint.coverage_sqm():.1f} sqm")
        print(f"Stats: {paint.stats()}")

if __name__ == "__main__":
    PaintMixing("white", 0, "blue").run()
