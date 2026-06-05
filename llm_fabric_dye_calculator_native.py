"""Native stdlib module: Fabric Dye Calculator
Calculates dye concentration, shade percentages, and chemical needs.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class FabricDyeCalculator:
    fabric_weight_g: float
    dye_type: str  # reactive, direct, acid, disperse, vat, natural
    desired_depth_pct: float = 2.0
    liquor_ratio: float = 10.0

    _DYE_OWFS = {
        "reactive": {"light": 0.5, "medium": 2.0, "dark": 4.0, "black": 6.0},
        "direct": {"light": 0.5, "medium": 1.5, "dark": 3.0, "black": 5.0},
        "acid": {"light": 0.5, "medium": 1.5, "dark": 3.0, "black": 4.0},
        "disperse": {"light": 0.5, "medium": 2.0, "dark": 4.0, "black": 6.0},
        "vat": {"light": 1.0, "medium": 3.0, "dark": 5.0, "black": 8.0},
        "natural": {"light": 5.0, "medium": 15.0, "dark": 30.0, "black": 50.0},
    }

    def depth_category(self) -> str:
        if self.desired_depth_pct < 1:
            return "light"
        elif self.desired_depth_pct < 3:
            return "medium"
        elif self.desired_depth_pct < 5:
            return "dark"
        return "black"

    def dye_needed_g(self) -> float:
        owf = self._DYE_OWFS.get(self.dye_type, {}).get(self.depth_category(), 2.0)
        return (self.fabric_weight_g / 100) * owf

    def salt_needed_g(self) -> float:
        if self.dye_type in ["reactive", "direct"]:
            return self.fabric_weight_g * (self.liquor_ratio / 10) * 20
        return 0

    def soda_ash_needed_g(self) -> float:
        if self.dye_type == "reactive":
            return self.fabric_weight_g * 0.05
        return 0

    def water_volume_l(self) -> float:
        return (self.fabric_weight_g / 1000) * self.liquor_ratio

    def fixative_needed_g(self) -> float:
        if self.dye_type == "acid":
            return self.fabric_weight_g * 0.02
        return 0

    def stats(self) -> Dict:
        return {
            "fabric_weight_g": self.fabric_weight_g,
            "dye_type": self.dye_type,
            "desired_depth_pct": self.desired_depth_pct,
            "depth_category": self.depth_category(),
            "dye_needed_g": round(self.dye_needed_g(), 2),
            "salt_needed_g": round(self.salt_needed_g(), 1),
            "soda_ash_needed_g": round(self.soda_ash_needed_g(), 2),
            "water_volume_l": round(self.water_volume_l(), 2),
            "fixative_needed_g": round(self.fixative_needed_g(), 2),
        }

def run():
    fdc = FabricDyeCalculator(fabric_weight_g=500, dye_type="reactive", desired_depth_pct=2.5, liquor_ratio=12)
    print(fdc.stats())

if __name__ == "__main__":
    run()
