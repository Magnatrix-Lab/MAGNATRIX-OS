"""Glaze Calculator — unity molecular, SiO2:Al2O3 ratio, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class GlazeCalculator:
    ingredients: Dict[str, Dict[str, float]] = field(default_factory=dict)
    """ingredient -> {SiO2, Al2O3, flux} mol%"""

    def unity_formula(self) -> Dict[str, float]:
        total = sum(d.get("flux", 0) for d in self.ingredients.values())
        if total == 0:
            return {}
        return {k: sum(d.get(k, 0) for d in self.ingredients.values()) / total for k in ["SiO2", "Al2O3", "flux"]}

    def silica_alumina_ratio(self) -> float:
        f = self.unity_formula()
        if not f.get("Al2O3", 0):
            return 0.0
        return f.get("SiO2", 0) / f.get("Al2O3", 0)

    def glaze_type(self) -> str:
        r = self.silica_alumina_ratio()
        if r > 12: return "matte"
        elif r > 6: return "satin"
        elif r > 3: return "glossy"
        return "crystalline"

    def expansion_coefficient(self) -> float:
        f = self.unity_formula()
        return 4.5 * f.get("SiO2", 0) + 1.5 * f.get("Al2O3", 0) + 15 * f.get("flux", 0)

    def stats(self) -> Dict:
        return {"unity": self.unity_formula(), "ratio": round(self.silica_alumina_ratio(), 2), "type": self.glaze_type()}

def run():
    gc = GlazeCalculator({
        "feldspar": {"SiO2": 0.6, "Al2O3": 0.25, "flux": 0.15},
        "silica": {"SiO2": 1.0, "Al2O3": 0, "flux": 0},
        "kaolin": {"SiO2": 0.45, "Al2O3": 0.4, "flux": 0.15},
    })
    print(gc.stats())

if __name__ == "__main__":
    run()
