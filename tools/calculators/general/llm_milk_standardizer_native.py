"""Native stdlib module: Milk Standardizer
Adjusts fat and protein content to target levels by cream addition or skimming.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class MilkStandardizer:
    current_volume_l: float
    current_fat_pct: float
    current_protein_pct: float
    target_fat_pct: float
    target_protein_pct: float
    cream_fat_pct: float = 40.0
    skim_fat_pct: float = 0.1

    def fat_adjustment_kg(self) -> float:
        current_fat_kg = self.current_volume_l * (self.current_fat_pct / 100)
        target_fat_kg = self.current_volume_l * (self.target_fat_pct / 100)
        return target_fat_kg - current_fat_kg

    def cream_to_add_l(self) -> float:
        adj = self.fat_adjustment_kg()
        if adj <= 0:
            return 0.0
        return adj / (self.cream_fat_pct / 100)

    def skim_to_add_l(self) -> float:
        adj = self.fat_adjustment_kg()
        if adj >= 0:
            return 0.0
        return abs(adj) / ((self.current_fat_pct - self.skim_fat_pct) / 100)

    def stats(self) -> Dict[str, float]:
        return {
            "fat_adjustment_kg": round(self.fat_adjustment_kg(), 3),
            "cream_to_add_l": round(self.cream_to_add_l(), 3),
            "skim_to_add_l": round(self.skim_to_add_l(), 3),
        }

def run():
    ms = MilkStandardizer(current_volume_l=1000, current_fat_pct=3.8, current_protein_pct=3.2,
                          target_fat_pct=3.5, target_protein_pct=3.2)
    print(ms.stats())

if __name__ == "__main__":
    run()
