"""Native stdlib module: Leather Thickness Calculator
Converts ounce weight, thickness, and gauge measurements for leather.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class LeatherThicknessCalculator:
    thickness_mm: Optional[float] = None
    ounce_weight: Optional[float] = None

    def mm_to_ounce(self) -> float:
        if self.thickness_mm is None:
            return 0
        return self.thickness_mm / 0.4

    def ounce_to_mm(self) -> float:
        if self.ounce_weight is None:
            return 0
        return self.ounce_weight * 0.4

    def thickness_iron(self) -> float:
        if self.thickness_mm is not None:
            return self.thickness_mm / 0.254
        if self.ounce_weight is not None:
            return self.ounce_to_mm() / 0.254
        return 0

    def classification(self) -> str:
        oz = self.mm_to_ounce() if self.thickness_mm is not None else (self.ounce_weight or 0)
        if oz < 2:
            return "garment"
        elif oz < 4:
            return "light_weight"
        elif oz < 6:
            return "medium_weight"
        elif oz < 8:
            return "heavy_weight"
        return "saddle_weight"

    def typical_use(self) -> str:
        cls = self.classification()
        uses = {
            "garment": "jackets, clothing",
            "light_weight": "wallets, small goods",
            "medium_weight": "bags, belts, shoes",
            "heavy_weight": "saddles, holsters, armor",
            "saddle_weight": "tooling, heavy harness",
        }
        return uses.get(cls, "general")

    def stats(self) -> Dict:
        return {
            "thickness_mm": round(self.thickness_mm, 2) if self.thickness_mm is not None else None,
            "ounce_weight": round(self.ounce_weight, 2) if self.ounce_weight is not None else None,
            "converted_mm": round(self.ounce_to_mm(), 2) if self.ounce_weight is not None else round(self.mm_to_ounce(), 2) if self.thickness_mm is not None else None,
            "thickness_iron": round(self.thickness_iron(), 1),
            "classification": self.classification(),
            "typical_use": self.typical_use(),
        }

def run():
    ltc = LeatherThicknessCalculator(thickness_mm=1.6)
    print(ltc.stats())

if __name__ == "__main__":
    run()
