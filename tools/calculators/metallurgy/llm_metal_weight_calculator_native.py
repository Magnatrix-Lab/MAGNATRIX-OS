"""Native stdlib module: Metal Weight Calculator
Calculates metal weights using specific gravity, volume, and dimensions.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class MetalWeightCalculator:
    metal_type: str
    volume_mm3: float

    _SPECIFIC_GRAVITY = {
        "gold": 19.32, "silver": 10.49, "platinum": 21.45, "copper": 8.96,
        "brass": 8.4, "bronze": 8.8, "aluminum": 2.7, "steel": 7.85,
        "titanium": 4.5, "nickel": 8.9, "zinc": 7.13, "lead": 11.34,
    }

    def specific_gravity(self) -> float:
        return self._SPECIFIC_GRAVITY.get(self.metal_type, 8.0)

    def weight_g(self) -> float:
        return self.volume_mm3 * (self.specific_gravity() / 1000)

    def weight_ozt(self) -> float:
        return self.weight_g() / 31.1035

    def weight_oz(self) -> float:
        return self.weight_g() / 28.3495

    def volume_from_weight_g(self, weight_g: float) -> float:
        if self.specific_gravity() == 0:
            return 0
        return weight_g / (self.specific_gravity() / 1000)

    def wire_length_mm(self, wire_diameter_mm: float) -> float:
        if wire_diameter_mm == 0:
            return 0
        radius = wire_diameter_mm / 2
        cross_section = 3.14159 * radius ** 2
        return self.volume_mm3 / cross_section

    def sheet_area_mm2(self, sheet_thickness_mm: float) -> float:
        if sheet_thickness_mm == 0:
            return 0
        return self.volume_mm3 / sheet_thickness_mm

    def stats(self, wire_diameter_mm: Optional[float] = None, sheet_thickness_mm: Optional[float] = None) -> Dict:
        result = {
            "metal_type": self.metal_type,
            "specific_gravity": self.specific_gravity(),
            "volume_mm3": self.volume_mm3,
            "weight_g": round(self.weight_g(), 2),
            "weight_ozt": round(self.weight_ozt(), 3),
            "weight_oz": round(self.weight_oz(), 3),
        }
        if wire_diameter_mm is not None:
            result["wire_length_mm"] = round(self.wire_length_mm(wire_diameter_mm), 1)
        if sheet_thickness_mm is not None:
            result["sheet_area_mm2"] = round(self.sheet_area_mm2(sheet_thickness_mm), 1)
        return result

def run():
    mwc = MetalWeightCalculator(metal_type="silver", volume_mm3=500)
    print(mwc.stats(wire_diameter_mm=1.0, sheet_thickness_mm=0.5))

if __name__ == "__main__":
    run()
