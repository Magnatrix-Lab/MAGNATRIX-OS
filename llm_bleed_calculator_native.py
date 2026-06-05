"""Native stdlib module: Bleed Calculator
Calculates bleed, trim, and safe zones for print layouts.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class BleedCalculator:
    trim_width_in: float
    trim_height_in: float
    bleed_in: float = 0.125
    safe_zone_in: float = 0.25

    def document_width(self) -> float:
        return self.trim_width_in + (2 * self.bleed_in)

    def document_height(self) -> float:
        return self.trim_height_in + (2 * self.bleed_in)

    def safe_width(self) -> float:
        return self.trim_width_in - (2 * self.safe_zone_in)

    def safe_height(self) -> float:
        return self.trim_height_in - (2 * self.safe_zone_in)

    def stats(self) -> Dict[str, float]:
        return {
            "trim_width": self.trim_width_in,
            "trim_height": self.trim_height_in,
            "document_width": round(self.document_width(), 3),
            "document_height": round(self.document_height(), 3),
            "safe_width": round(self.safe_width(), 3),
            "safe_height": round(self.safe_height(), 3),
            "bleed": self.bleed_in,
        }

def run():
    bc = BleedCalculator(trim_width_in=8.5, trim_height_in=11, bleed_in=0.125, safe_zone_in=0.25)
    print(bc.stats())

if __name__ == "__main__":
    run()
