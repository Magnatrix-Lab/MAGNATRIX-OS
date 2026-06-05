"""Native stdlib module: Spirit Dilution Calculator
Dilutes spirits to target ABV using water or other spirits.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class SpiritDilutionCalculator:
    spirit_volume_l: float
    spirit_abv_pct: float
    target_abv_pct: float

    def water_to_add_l(self) -> float:
        if self.target_abv_pct == 0:
            return 0
        return (self.spirit_volume_l * self.spirit_abv_pct / self.target_abv_pct) - self.spirit_volume_l

    def final_volume_l(self) -> float:
        return self.spirit_volume_l + self.water_to_add_l()

    def dilution_ratio(self) -> float:
        if self.spirit_volume_l == 0:
            return 0
        return self.water_to_add_l() / self.spirit_volume_l

    def proof(self) -> float:
        return self.target_abv_pct * 2

    def original_proof(self) -> float:
        return self.spirit_abv_pct * 2

    def abv_reduction_pct(self) -> float:
        if self.spirit_abv_pct == 0:
            return 0
        return ((self.spirit_abv_pct - self.target_abv_pct) / self.spirit_abv_pct) * 100

    def is_possible(self) -> bool:
        return self.target_abv_pct <= self.spirit_abv_pct and self.target_abv_pct > 0

    def stats(self) -> Dict:
        return {
            "spirit_volume_l": self.spirit_volume_l,
            "spirit_abv_pct": self.spirit_abv_pct,
            "target_abv_pct": self.target_abv_pct,
            "water_to_add_l": round(self.water_to_add_l(), 3),
            "final_volume_l": round(self.final_volume_l(), 3),
            "dilution_ratio": round(self.dilution_ratio(), 3),
            "proof": self.proof(),
            "abv_reduction_pct": round(self.abv_reduction_pct(), 1),
            "is_possible": self.is_possible(),
        }

def run():
    sdc = SpiritDilutionCalculator(spirit_volume_l=2, spirit_abv_pct=65, target_abv_pct=40)
    print(sdc.stats())

if __name__ == "__main__":
    run()
