"""Native stdlib module: Polymer Blend Calculator
Calculates polymer blend ratios, compatibilizer needs, and property estimates.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class PolymerComponent:
    name: str
    weight_pct: float
    density_g_cm3: float
    melt_index_g_10min: float
    tensile_strength_mpa: float

@dataclass
class PolymerBlendCalculator:
    blend_name: str
    components: List[PolymerComponent] = field(default_factory=list)

    def total_weight_pct(self) -> float:
        return sum(c.weight_pct for c in self.components)

    def blend_density_g_cm3(self) -> float:
        if self.total_weight_pct() == 0:
            return 0.0
        total = 0.0
        for c in self.components:
            total += c.weight_pct / c.density_g_cm3
        return self.total_weight_pct() / total if total > 0 else 0.0

    def weighted_tensile_strength_mpa(self) -> float:
        if self.total_weight_pct() == 0:
            return 0.0
        return sum(c.weight_pct * c.tensile_strength_mpa for c in self.components) / self.total_weight_pct()

    def weighted_melt_index(self) -> float:
        if self.total_weight_pct() == 0:
            return 0.0
        return sum(c.weight_pct * c.melt_index_g_10min for c in self.components) / self.total_weight_pct()

    def compatibilizer_needed(self) -> bool:
        return len(self.components) > 2 or any(c.weight_pct < 20 for c in self.components)

    def stats(self) -> Dict:
        return {
            "blend": self.blend_name,
            "components": len(self.components),
            "total_weight_pct": round(self.total_weight_pct(), 1),
            "blend_density": round(self.blend_density_g_cm3(), 3),
            "weighted_tensile": round(self.weighted_tensile_strength_mpa(), 1),
            "weighted_melt_index": round(self.weighted_melt_index(), 2),
            "compatibilizer_needed": self.compatibilizer_needed(),
        }

def run():
    pbc = PolymerBlendCalculator(
        blend_name="PP-PE Blend",
        components=[
            PolymerComponent("PP", 70, 0.905, 12, 35),
            PolymerComponent("PE", 30, 0.92, 8, 25),
        ]
    )
    print(pbc.stats())

if __name__ == "__main__":
    run()
