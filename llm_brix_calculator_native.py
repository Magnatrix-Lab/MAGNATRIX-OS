"""Native stdlib module: Brix Calculator
Converts between Brix, specific gravity, potential alcohol, and Plato.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class BrixCalculator:
    brix: float

    def specific_gravity(self) -> float:
        return 1 + (self.brix / (258.6 - ((self.brix / 258.2) * 227.1)))

    def plato(self) -> float:
        return self.brix * 1.04

    def potential_abv(self, final_brix: float = 0) -> float:
        return (self.brix - final_brix) * 0.59

    def dissolved_solids_g_l(self) -> float:
        return self.brix * 10

    def sugar_content_g(self, volume_l: float) -> float:
        return self.dissolved_solids_g_l() * volume_l

    def water_activity_estimate(self) -> float:
        if self.brix == 0:
            return 1.0
        return 0.995 - (self.brix * 0.003)

    def stats(self, volume_l: float = 0) -> Dict:
        return {
            "brix": self.brix,
            "specific_gravity": round(self.specific_gravity(), 4),
            "plato": round(self.plato(), 2),
            "potential_abv": round(self.potential_abv(), 1),
            "dissolved_solids_g_l": round(self.dissolved_solids_g_l(), 1),
            "sugar_content_g": round(self.sugar_content_g(volume_l), 1) if volume_l else None,
        }

def run():
    bc = BrixCalculator(brix=20)
    print(bc.stats(volume_l=50))

if __name__ == "__main__":
    run()
