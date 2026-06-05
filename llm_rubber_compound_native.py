"""Rubber Compound Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

class RubberType(Enum):
    NATURAL = "natural"
    SBR = "styrene_butadiene"
    NBR = "nitrile"
    EPDM = "ethylene_propylene"
    SILICONE = "silicone"

@dataclass
class RubberCompound:
    rubber_type: RubberType
    base_polymer_kg: float
    filler_percent: float = 30.0
    plasticizer_percent: float = 5.0
    curatives_percent: float = 8.0
    additives: Dict[str, float] = field(default_factory=dict)

    def total_weight(self) -> float:
        filler = self.base_polymer_kg * self.filler_percent / 100.0
        plasticizer = self.base_polymer_kg * self.plasticizer_percent / 100.0
        curatives = self.base_polymer_kg * self.curatives_percent / 100.0
        additives = sum(self.additives.values())
        return self.base_polymer_kg + filler + plasticizer + curatives + additives

    def composition(self) -> Dict[str, float]:
        total = self.total_weight()
        if total == 0:
            return {}
        filler = self.base_polymer_kg * self.filler_percent / 100.0
        plasticizer = self.base_polymer_kg * self.plasticizer_percent / 100.0
        curatives = self.base_polymer_kg * self.curatives_percent / 100.0
        result = {
            "base_polymer": round(self.base_polymer_kg / total * 100, 2),
            "filler": round(filler / total * 100, 2),
            "plasticizer": round(plasticizer / total * 100, 2),
            "curatives": round(curatives / total * 100, 2),
        }
        for name, qty in self.additives.items():
            result[name] = round(qty / total * 100, 2)
        return result

    def cost_estimate(self, polymer_price_per_kg: float,
                      filler_price: float = 1.0,
                      plasticizer_price: float = 3.0,
                      curatives_price: float = 5.0) -> float:
        filler = self.base_polymer_kg * self.filler_percent / 100.0
        plasticizer = self.base_polymer_kg * self.plasticizer_percent / 100.0
        curatives = self.base_polymer_kg * self.curatives_percent / 100.0
        cost = (self.base_polymer_kg * polymer_price_per_kg +
                filler * filler_price +
                plasticizer * plasticizer_price +
                curatives * curatives_price)
        return round(cost, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "total_weight_kg": round(self.total_weight(), 3),
            "base_polymer_ratio": round(self.base_polymer_kg / self.total_weight() * 100, 2) if self.total_weight() > 0 else 0,
        }

    def run(self):
        print("=" * 60)
        print("RUBBER COMPOUND CALCULATOR")
        print("=" * 60)
        compound = RubberCompound(
            rubber_type=RubberType.NBR,
            base_polymer_kg=100.0,
            filler_percent=35.0,
            plasticizer_percent=8.0,
            curatives_percent=10.0,
            additives={"antioxidant": 2.0, "accelerator": 1.5}
        )
        print(f"Compound: {compound.rubber_type.value}")
        print(f"Total weight: {compound.total_weight():.2f} kg")
        print(f"Composition: {compound.composition()}")
        print(f"Cost estimate: ${compound.cost_estimate(polymer_price_per_kg=4.5):.2f}")
        print(f"Stats: {compound.stats()}")

if __name__ == "__main__":
    RubberCompound(RubberType.NATURAL, 0).run()
