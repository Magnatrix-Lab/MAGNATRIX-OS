"""Metal Casting Yield Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class MetalCastingYield:
    metal_type: str
    pour_weight_kg: float
    finished_weight_kg: float
    scrap_weight_kg: float = 0.0

    def casting_yield_percent(self) -> float:
        if self.pour_weight_kg <= 0:
            return 0.0
        return round(self.finished_weight_kg / self.pour_weight_kg * 100, 2)

    def scrap_rate_percent(self) -> float:
        if self.pour_weight_kg <= 0:
            return 0.0
        return round(self.scrap_weight_kg / self.pour_weight_kg * 100, 2)

    def material_efficiency(self) -> float:
        if self.pour_weight_kg <= 0:
            return 0.0
        return round((self.finished_weight_kg + self.scrap_weight_kg) / self.pour_weight_kg * 100, 2)

    def shrinkage_allowance_percent(self) -> float:
        shrinkages = {"iron": 1.0, "aluminum": 1.3, "copper": 1.6, "steel": 2.0, "bronze": 1.5, "brass": 1.5}
        return shrinkages.get(self.metal_type, 1.5)

    def pattern_dimensions(self, final_dimension_mm: float) -> float:
        return round(final_dimension_mm * (1 + self.shrinkage_allowance_percent() / 100.0), 2)

    def gating_system_weight_kg(self) -> float:
        return round(self.pour_weight_kg - self.finished_weight_kg - self.scrap_weight_kg, 2)

    def recycle_rate_percent(self) -> float:
        if self.pour_weight_kg <= 0:
            return 0.0
        return round((self.scrap_weight_kg + self.gating_system_weight_kg()) / self.pour_weight_kg * 100, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "casting_yield_percent": self.casting_yield_percent(),
            "scrap_rate_percent": self.scrap_rate_percent(),
            "shrinkage_allowance": self.shrinkage_allowance_percent(),
        }

    def run(self):
        print("=" * 60)
        print("METAL CASTING YIELD CALCULATOR")
        print("=" * 60)
        cy = MetalCastingYield(
            metal_type="aluminum", pour_weight_kg=100, finished_weight_kg=70, scrap_weight_kg=5
        )
        print(f"Metal: {cy.metal_type}")
        print(f"Pour: {cy.pour_weight_kg} kg")
        print(f"Finished: {cy.finished_weight_kg} kg")
        print(f"Yield: {cy.casting_yield_percent():.2f}%")
        print(f"Scrap rate: {cy.scrap_rate_percent():.2f}%")
        print(f"Shrinkage: {cy.shrinkage_allowance_percent():.2f}%")
        print(f"Gating system: {cy.gating_system_weight_kg():.2f} kg")
        print(f"Recycle rate: {cy.recycle_rate_percent():.2f}%")
        print(f"Stats: {cy.stats()}")

if __name__ == "__main__":
    MetalCastingYield("iron", 0, 0).run()
