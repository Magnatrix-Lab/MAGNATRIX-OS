"""Native stdlib module: Crop Yield Estimator
Estimates crop yield by planting area, seed rate, and environmental factors.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class CropType(Enum):
    WHEAT = "wheat"
    CORN = "corn"
    RICE = "rice"
    SOYBEAN = "soybean"
    COTTON = "cotton"

@dataclass
class CropYieldEstimator:
    crop_type: CropType
    area_hectares: float
    seed_rate_kg_per_ha: float
    expected_yield_tons_per_ha: float
    moisture_pct: float = 13.0

    def total_seed_kg(self) -> float:
        return self.area_hectares * self.seed_rate_kg_per_ha

    def gross_yield_tons(self) -> float:
        return self.area_hectares * self.expected_yield_tons_per_ha

    def dry_yield_tons(self) -> float:
        return self.gross_yield_tons() * (1 - self.moisture_pct / 100)

    def revenue(self, price_per_ton: float) -> float:
        return self.gross_yield_tons() * price_per_ton

    def stats(self, price_per_ton: float = 0) -> Dict:
        return {
            "crop": self.crop_type.value,
            "area_ha": self.area_hectares,
            "total_seed_kg": round(self.total_seed_kg(), 1),
            "gross_yield_tons": round(self.gross_yield_tons(), 1),
            "dry_yield_tons": round(self.dry_yield_tons(), 1),
            "revenue": round(self.revenue(price_per_ton), 2) if price_per_ton else None,
        }

def run():
    cy = CropYieldEstimator(crop_type=CropType.WHEAT, area_hectares=50, seed_rate_kg_per_ha=120, expected_yield_tons_per_ha=4.5, moisture_pct=13)
    print(cy.stats(price_per_ton=250))

if __name__ == "__main__":
    run()
