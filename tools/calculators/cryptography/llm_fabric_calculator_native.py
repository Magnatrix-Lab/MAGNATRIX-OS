"""Native stdlib module: Fabric Calculator
Calculates fabric requirements, yield, and cost for garment production.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class FabricType(Enum):
    COTTON = "cotton"
    POLYESTER = "polyester"
    LINEN = "linen"
    SILK = "silk"
    WOOL = "wool"
    DENIM = "denim"

@dataclass
class PatternPiece:
    name: str
    width_cm: float
    length_cm: float
    quantity: int

@dataclass
class FabricCalculator:
    fabric_type: FabricType
    fabric_width_cm: float
    pattern_pieces: List[PatternPiece] = field(default_factory=list)
    fabric_cost_per_m: float = 0.0

    def piece_area_cm2(self, piece: PatternPiece) -> float:
        return piece.width_cm * piece.length_cm * piece.quantity

    def total_area_cm2(self) -> float:
        return sum(self.piece_area_cm2(p) for p in self.pattern_pieces)

    def fabric_length_m(self, efficiency_pct: float = 85) -> float:
        if self.fabric_width_cm == 0 or efficiency_pct == 0:
            return 0.0
        usable_width = self.fabric_width_cm * (efficiency_pct / 100)
        total_length_cm = sum(p.length_cm * p.quantity for p in self.pattern_pieces)
        return total_length_cm / 100

    def fabric_cost(self, efficiency_pct: float = 85) -> float:
        return self.fabric_length_m(efficiency_pct) * self.fabric_cost_per_m

    def yield_per_m2(self) -> float:
        fabric_area_m2 = (self.fabric_width_cm / 100) * self.fabric_length_m()
        if fabric_area_m2 == 0:
            return 0.0
        return (self.total_area_cm2() / 10000) / fabric_area_m2

    def stats(self) -> Dict:
        return {
            "fabric": self.fabric_type.value,
            "pieces": len(self.pattern_pieces),
            "total_area_cm2": round(self.total_area_cm2(), 1),
            "fabric_length_m": round(self.fabric_length_m(), 2),
            "fabric_cost": round(self.fabric_cost(), 2),
            "yield_per_m2": round(self.yield_per_m2(), 3),
        }

def run():
    fc = FabricCalculator(
        fabric_type=FabricType.COTTON,
        fabric_width_cm=140,
        fabric_cost_per_m=8.5,
        pattern_pieces=[
            PatternPiece("front", 50, 60, 2),
            PatternPiece("back", 50, 60, 2),
            PatternPiece("sleeve", 25, 55, 2),
            PatternPiece("collar", 8, 40, 1),
        ]
    )
    print(fc.stats())

if __name__ == "__main__":
    run()
