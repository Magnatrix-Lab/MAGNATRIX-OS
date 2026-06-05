"""Native stdlib module: Chocolate Mold Calculator
Calculates mold capacity, chocolate needs, and batch yield.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class ChocolateMoldCalculator:
    mold_cavity_count: int
    cavity_volume_ml: float
    chocolate_density_g_per_ml: float = 1.3
    waste_factor_pct: float = 10.0

    def chocolate_per_cavity_g(self) -> float:
        return self.cavity_volume_ml * self.chocolate_density_g_per_ml

    def total_chocolate_g(self) -> float:
        return self.chocolate_per_cavity_g() * self.mold_cavity_count

    def chocolate_with_waste_g(self) -> float:
        return self.total_chocolate_g() * (1 + self.waste_factor_pct / 100)

    def batch_yield_pieces(self) -> int:
        return self.mold_cavity_count

    def molds_per_kg(self) -> float:
        if self.total_chocolate_g() == 0:
            return 0
        return 1000 / self.total_chocolate_g()

    def cost_per_piece(self, chocolate_cost_per_kg: float) -> float:
        if self.mold_cavity_count == 0:
            return 0
        return (self.chocolate_with_waste_g() / 1000 * chocolate_cost_per_kg) / self.mold_cavity_count

    def stats(self, chocolate_cost_per_kg: float = 15.0) -> Dict:
        return {
            "mold_cavity_count": self.mold_cavity_count,
            "cavity_volume_ml": self.cavity_volume_ml,
            "chocolate_per_cavity_g": round(self.chocolate_per_cavity_g(), 1),
            "total_chocolate_g": round(self.total_chocolate_g(), 1),
            "chocolate_with_waste_g": round(self.chocolate_with_waste_g(), 1),
            "batch_yield_pieces": self.batch_yield_pieces(),
            "molds_per_kg": round(self.molds_per_kg(), 2),
            "cost_per_piece_usd": round(self.cost_per_piece(chocolate_cost_per_kg), 2),
        }

def run():
    cmc = ChocolateMoldCalculator(mold_cavity_count=24, cavity_volume_ml=15, chocolate_density_g_per_ml=1.3, waste_factor_pct=15)
    print(cmc.stats())

if __name__ == "__main__":
    run()
