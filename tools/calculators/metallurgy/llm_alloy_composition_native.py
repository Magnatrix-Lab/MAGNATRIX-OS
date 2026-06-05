"""Alloy Composition Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class AlloyComposition:
    base_metal: str
    total_weight_kg: float
    elements: Dict[str, float] = field(default_factory=dict)

    def base_metal_weight_kg(self) -> float:
        return round(self.total_weight_kg - sum(self.elements.values()), 3)

    def base_metal_percent(self) -> float:
        if self.total_weight_kg <= 0:
            return 0.0
        return round(self.base_metal_weight_kg() / self.total_weight_kg * 100, 2)

    def element_percent(self, element: str) -> float:
        if self.total_weight_kg <= 0:
            return 0.0
        return round(self.elements.get(element, 0) / self.total_weight_kg * 100, 2)

    def composition(self) -> Dict[str, float]:
        if self.total_weight_kg <= 0:
            return {}
        result = {self.base_metal: self.base_metal_percent()}
        for el, w in self.elements.items():
            result[el] = round(w / self.total_weight_kg * 100, 2)
        return result

    def density_estimate_kg_m3(self) -> float:
        densities = {"iron": 7874, "aluminum": 2700, "copper": 8960, "titanium": 4500, "nickel": 8908}
        base = densities.get(self.base_metal, 8000)
        for el, w in self.elements.items():
            d = {"carbon": 2260, "chromium": 7190, "manganese": 7210, "silicon": 2330, "molybdenum": 10280}
            base = base * 0.9 + d.get(el, base) * 0.1
        return round(base, 1)

    def cost_estimate(self, prices: Dict[str, float]) -> float:
        cost = self.base_metal_weight_kg() * prices.get(self.base_metal, 2.0)
        for el, w in self.elements.items():
            cost += w * prices.get(el, 10.0)
        return round(cost, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "base_metal_percent": self.base_metal_percent(),
            "total_weight_kg": self.total_weight_kg,
            "density_estimate": self.density_estimate_kg_m3(),
        }

    def run(self):
        print("=" * 60)
        print("ALLOY COMPOSITION CALCULATOR")
        print("=" * 60)
        alloy = AlloyComposition(
            base_metal="iron", total_weight_kg=1000,
            elements={"carbon": 18, "chromium": 180, "manganese": 10, "silicon": 5}
        )
        print(f"Base: {alloy.base_metal}")
        print(f"Composition: {alloy.composition()}")
        print(f"Base metal %: {alloy.base_metal_percent():.2f}%")
        print(f"Density: {alloy.density_estimate_kg_m3():.1f} kg/m3")
        print(f"Stats: {alloy.stats()}")

if __name__ == "__main__":
    AlloyComposition("iron", 0).run()
