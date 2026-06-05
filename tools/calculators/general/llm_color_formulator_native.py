"""Color Formulator — pigment, dye, concentration, mixing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class ColorFormulator:
    pigments: Dict[str, float] = field(default_factory=dict)
    """pigment name -> concentration %"""
    base_white: float = 100.0

    def total_pigment(self) -> float:
        return sum(self.pigments.values())

    def tint_strength(self) -> float:
        return min(1.0, self.total_pigment() / 10)

    def opacity(self, refractive_index: float = 2.5) -> float:
        return 1 - math.exp(-0.5 * self.total_pigment() * (refractive_index - 1.5))

    def mixture(self, other: 'ColorFormulator') -> Dict[str, float]:
        result = dict(self.pigments)
        for k, v in other.pigments.items():
            result[k] = result.get(k, 0) + v
        return result

    def delta_e(self, lab1: Tuple[float, float, float], lab2: Tuple[float, float, float]) -> float:
        import math
        return math.sqrt(sum((a - b)**2 for a, b in zip(lab1, lab2)))

    def stats(self) -> Dict:
        return {"total_pigment": round(self.total_pigment(), 2), "tint_strength": round(self.tint_strength(), 3), "opacity": round(self.opacity(), 3)}

def run():
    import math
    cf = ColorFormulator({"titanium_dioxide": 5, "red_oxide": 2, "yellow_oxide": 1})
    print(cf.stats())
    print("Delta E:", cf.delta_e((50, 10, 20), (55, 12, 18)))

if __name__ == "__main__":
    run()
