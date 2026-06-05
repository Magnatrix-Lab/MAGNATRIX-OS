"""Native stdlib module: Strip Ratio Calculator
Calculates strip ratios, overburden volumes, and pit optimization for open-pit mining.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class StripRatioCalculator:
    ore_tonnes: float
    waste_tonnes: float
    ore_density_ton_m3: float = 2.7
    waste_density_ton_m3: float = 2.0

    def strip_ratio_ton_ton(self) -> float:
        if self.ore_tonnes == 0:
            return 0.0
        return self.waste_tonnes / self.ore_tonnes

    def strip_ratio_m3_m3(self) -> float:
        if self.ore_tonnes == 0:
            return 0.0
        ore_m3 = self.ore_tonnes / self.ore_density_ton_m3
        waste_m3 = self.waste_tonnes / self.waste_density_ton_m3
        return waste_m3 / ore_m3

    def total_material_tonnes(self) -> float:
        return self.ore_tonnes + self.waste_tonnes

    def ore_pct(self) -> float:
        if self.total_material_tonnes() == 0:
            return 0.0
        return (self.ore_tonnes / self.total_material_tonnes()) * 100

    def waste_pct(self) -> float:
        if self.total_material_tonnes() == 0:
            return 0.0
        return (self.waste_tonnes / self.total_material_tonnes()) * 100

    def max_economic_strip_ratio(self, ore_value_usd_ton: float, mining_cost_usd_ton: float) -> float:
        if mining_cost_usd_ton == 0:
            return 0.0
        return (ore_value_usd_ton / mining_cost_usd_ton) - 1

    def stats(self, ore_value_usd_ton: float = 0, mining_cost_usd_ton: float = 0) -> Dict:
        return {
            "strip_ratio_ton_ton": round(self.strip_ratio_ton_ton(), 2),
            "strip_ratio_m3_m3": round(self.strip_ratio_m3_m3(), 2),
            "total_material_tonnes": round(self.total_material_tonnes(), 1),
            "ore_pct": round(self.ore_pct(), 1),
            "waste_pct": round(self.waste_pct(), 1),
            "max_economic_strip_ratio": round(self.max_economic_strip_ratio(ore_value_usd_ton, mining_cost_usd_ton), 2) if ore_value_usd_ton and mining_cost_usd_ton else None,
        }

def run():
    src = StripRatioCalculator(ore_tonnes=500000, waste_tonnes=1500000)
    print(src.stats(ore_value_usd_ton=80, mining_cost_usd_ton=20))

if __name__ == "__main__":
    run()
