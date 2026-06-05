"""Native stdlib module: Metal Alloy Calculator
Calculates alloy recipes, karat purity, fineness, and metal weights.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class MetalAlloyCalculator:
    total_weight_g: float
    alloy_type: str  # gold, silver, platinum, copper
    karat: Optional[float] = None
    fineness: Optional[float] = None

    def pure_metal_g(self) -> float:
        if self.karat is not None and self.alloy_type == "gold":
            return self.total_weight_g * (self.karat / 24)
        if self.fineness is not None:
            return self.total_weight_g * (self.fineness / 1000)
        if self.alloy_type == "silver":
            return self.total_weight_g * 0.925
        if self.alloy_type == "copper":
            return self.total_weight_g * 0.99
        return self.total_weight_g

    def alloy_metal_g(self) -> float:
        return self.total_weight_g - self.pure_metal_g()

    def karat_from_fineness(self) -> float:
        if self.fineness is None:
            return 0
        return (self.fineness / 1000) * 24

    def fineness_from_karat(self) -> float:
        if self.karat is None:
            return 0
        return (self.karat / 24) * 1000

    def value_at_spot(self, spot_price_per_oz_usd: float, pure_metal_oz_per_g: float = 0.03215) -> float:
        pure_oz = self.pure_metal_g() * pure_metal_oz_per_g
        return pure_oz * spot_price_per_oz_usd

    def stats(self, spot_price_per_oz_usd: Optional[float] = None) -> Dict:
        result = {
            "alloy_type": self.alloy_type,
            "total_weight_g": self.total_weight_g,
            "pure_metal_g": round(self.pure_metal_g(), 2),
            "alloy_metal_g": round(self.alloy_metal_g(), 2),
            "purity_pct": round(self.pure_metal_g() / self.total_weight_g * 100, 1) if self.total_weight_g else 0,
        }
        if self.karat is not None:
            result["karat"] = self.karat
            result["fineness"] = round(self.fineness_from_karat(), 1)
        if self.fineness is not None:
            result["fineness"] = self.fineness
            result["karat"] = round(self.karat_from_fineness(), 1)
        if spot_price_per_oz_usd is not None:
            result["value_at_spot_usd"] = round(self.value_at_spot(spot_price_per_oz_usd), 2)
        return result

def run():
    mac = MetalAlloyCalculator(total_weight_g=10, alloy_type="gold", karat=18, spot_price_per_oz_usd=2000)
    print(mac.stats())

if __name__ == "__main__":
    run()
