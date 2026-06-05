"""Native stdlib module: Spice Blender
Formulates spice blends by weight ratios, heat levels, and flavor profiles.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class HeatLevel(Enum):
    MILD = 1
    MEDIUM = 2
    HOT = 3
    EXTRA_HOT = 4

@dataclass
class SpiceComponent:
    name: str
    weight_g: float
    heat_units: int = 0

@dataclass
class SpiceBlender:
    blend_name: str
    total_weight_g: float
    components: List[SpiceComponent] = field(default_factory=list)

    def current_weight(self) -> float:
        return sum(c.weight_g for c in self.components)

    def heat_level(self) -> HeatLevel:
        total_heat = sum(c.heat_units for c in self.components)
        if total_heat <= 2:
            return HeatLevel.MILD
        elif total_heat <= 5:
            return HeatLevel.MEDIUM
        elif total_heat <= 10:
            return HeatLevel.HOT
        return HeatLevel.EXTRA_HOT

    def remaining_g(self) -> float:
        return max(0, self.total_weight_g - self.current_weight())

    def stats(self) -> Dict:
        return {
            "current_weight_g": round(self.current_weight(), 1),
            "target_weight_g": self.total_weight_g,
            "remaining_g": round(self.remaining_g(), 1),
            "heat_level": self.heat_level().name,
            "components": len(self.components),
        }

def run():
    sb = SpiceBlender(
        blend_name="Garam Masala",
        total_weight_g=500,
        components=[
            SpiceComponent("coriander", 120, 0),
            SpiceComponent("cumin", 80, 1),
            SpiceComponent("cardamom", 40, 0),
            SpiceComponent("black pepper", 30, 2),
            SpiceComponent("cinnamon", 50, 0),
            SpiceComponent("clove", 20, 1),
            SpiceComponent("nutmeg", 20, 0),
        ]
    )
    print(sb.stats())

if __name__ == "__main__":
    run()
