"""Textile Analyzer — fiber blend, GSM, tensile, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class TextileAnalyzer:
    fiber_blend: Dict = field(default_factory=dict)
    gsm: float = 180.0

    def blend_total(self) -> float:
        return sum(self.fiber_blend.values())

    def blend_percentage(self, fiber: str) -> float:
        return (self.fiber_blend.get(fiber, 0) / self.blend_total() * 100.0) if self.blend_total() > 0 else 0.0

    def fabric_weight(self, area_m2: float = 1.0) -> float:
        return area_m2 * self.gsm / 1000.0

    def stats(self) -> Dict:
        return {"blend_total": round(self.blend_total(), 2), "fabric_weight_kg": round(self.fabric_weight(2.5), 3)}

def run():
    ta = TextileAnalyzer(fiber_blend={"cotton": 60, "polyester": 40}, gsm=200)
    print(ta.stats())

if __name__ == "__main__":
    run()
