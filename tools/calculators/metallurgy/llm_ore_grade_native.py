"""Native stdlib module: Ore Grade Calculator
Calculates ore grade, cut-off grade, and metal recovery for mining operations.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class MetalType(Enum):
    GOLD = "gold"
    SILVER = "silver"
    COPPER = "copper"
    IRON = "iron"
    ZINC = "zinc"
    LEAD = "lead"

@dataclass
class OreGradeCalculator:
    ore_tonnes: float
    metal_grade_pct: float
    metal_type: MetalType
    recovery_pct: float
    metal_price_usd_per_kg: float
    mining_cost_usd_per_ton: float
    processing_cost_usd_per_ton: float

    def contained_metal_kg(self) -> float:
        return self.ore_tonnes * 1000 * (self.metal_grade_pct / 100)

    def recovered_metal_kg(self) -> float:
        return self.contained_metal_kg() * (self.recovery_pct / 100)

    def revenue(self) -> float:
        return self.recovered_metal_kg() * self.metal_price_usd_per_kg

    def total_cost(self) -> float:
        return (self.mining_cost_usd_per_ton + self.processing_cost_usd_per_ton) * self.ore_tonnes

    def profit(self) -> float:
        return self.revenue() - self.total_cost()

    def cut_off_grade_pct(self) -> float:
        if self.metal_price_usd_per_kg == 0:
            return 0.0
        total_cost_per_ton = self.mining_cost_usd_per_ton + self.processing_cost_usd_per_ton
        return (total_cost_per_ton / (self.metal_price_usd_per_kg * 1000 * (self.recovery_pct / 100))) * 100

    def profit_per_ton(self) -> float:
        if self.ore_tonnes == 0:
            return 0.0
        return self.profit() / self.ore_tonnes

    def stats(self) -> Dict:
        return {
            "metal": self.metal_type.value,
            "contained_metal_kg": round(self.contained_metal_kg(), 1),
            "recovered_metal_kg": round(self.recovered_metal_kg(), 1),
            "revenue": round(self.revenue(), 2),
            "total_cost": round(self.total_cost(), 2),
            "profit": round(self.profit(), 2),
            "cut_off_grade_pct": round(self.cut_off_grade_pct(), 3),
            "profit_per_ton": round(self.profit_per_ton(), 2),
        }

def run():
    ogc = OreGradeCalculator(ore_tonnes=100000, metal_grade_pct=1.5, metal_type=MetalType.COPPER, recovery_pct=88, metal_price_usd_per_kg=8.5, mining_cost_usd_per_ton=25, processing_cost_usd_per_ton=35)
    print(ogc.stats())

if __name__ == "__main__":
    run()
