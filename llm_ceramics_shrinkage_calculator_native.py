"""Native stdlib module: Ceramics Shrinkage Calculator
Calculates drying and firing shrinkage for ceramics pieces.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class CeramicsShrinkageCalculator:
    wet_length_mm: float
    dry_length_mm: float
    fired_length_mm: float

    def drying_shrinkage_pct(self) -> float:
        if self.wet_length_mm == 0:
            return 0.0
        return ((self.wet_length_mm - self.dry_length_mm) / self.wet_length_mm) * 100

    def firing_shrinkage_pct(self) -> float:
        if self.dry_length_mm == 0:
            return 0.0
        return ((self.dry_length_mm - self.fired_length_mm) / self.dry_length_mm) * 100

    def total_shrinkage_pct(self) -> float:
        if self.wet_length_mm == 0:
            return 0.0
        return ((self.wet_length_mm - self.fired_length_mm) / self.wet_length_mm) * 100

    def expected_fired_size(self, wet_size_mm: float) -> float:
        total = self.total_shrinkage_pct()
        return wet_size_mm * (1 - total / 100)

    def wet_size_needed(self, target_fired_size_mm: float) -> float:
        total = self.total_shrinkage_pct()
        if total >= 100:
            return target_fired_size_mm
        return target_fired_size_mm / (1 - total / 100)

    def stats(self) -> Dict:
        return {
            "drying_shrinkage_pct": round(self.drying_shrinkage_pct(), 2),
            "firing_shrinkage_pct": round(self.firing_shrinkage_pct(), 2),
            "total_shrinkage_pct": round(self.total_shrinkage_pct(), 2),
            "wet_length_mm": self.wet_length_mm,
            "dry_length_mm": self.dry_length_mm,
            "fired_length_mm": self.fired_length_mm,
        }

def run():
    csc = CeramicsShrinkageCalculator(wet_length_mm=200, dry_length_mm=185, fired_length_mm=170)
    print(csc.stats())
    print("wet_size_needed for 150mm target:", round(csc.wet_size_needed(150), 1))

if __name__ == "__main__":
    run()
