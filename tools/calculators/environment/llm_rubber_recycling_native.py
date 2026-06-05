"""Rubber Recycling Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class RubberRecycling:
    scrap_weight_kg: float
    contamination_percent: float = 2.0
    recycling_method: str = "devulcanization"
    energy_per_kg_kwh: float = 0.8
    transport_distance_km: float = 100.0

    def recoverable_rubber_kg(self) -> float:
        loss = 1 + self.contamination_percent / 100.0
        return round(self.scrap_weight_kg / loss, 2)

    def recycling_yield_percent(self) -> float:
        yields = {"devulcanization": 75, "pyrolysis": 45, "grinding": 85, "reclaiming": 70}
        return yields.get(self.recycling_method, 60)

    def final_product_kg(self) -> float:
        recoverable = self.recoverable_rubber_kg()
        yield_pct = self.recycling_yield_percent()
        return round(recoverable * yield_pct / 100.0, 2)

    def energy_consumption_kwh(self) -> float:
        return round(self.scrap_weight_kg * self.energy_per_kg_kwh, 2)

    def transport_emissions_kg_co2(self) -> float:
        emission_factor = 0.12
        return round(self.scrap_weight_kg * self.transport_distance_km * emission_factor / 1000.0, 3)

    def cost_savings(self, virgin_price_per_kg: float = 3.0,
                     recycled_price_per_kg: float = 1.5) -> float:
        product = self.final_product_kg()
        return round(product * (virgin_price_per_kg - recycled_price_per_kg), 2)

    def stats(self) -> Dict[str, float]:
        return {
            "recoverable_rubber_kg": self.recoverable_rubber_kg(),
            "final_product_kg": self.final_product_kg(),
            "recycling_yield_percent": self.recycling_yield_percent(),
        }

    def run(self):
        print("=" * 60)
        print("RUBBER RECYCLING CALCULATOR")
        print("=" * 60)
        rec = RubberRecycling(
            scrap_weight_kg=1000.0, contamination_percent=3.0,
            recycling_method="devulcanization", energy_per_kg_kwh=0.9
        )
        print(f"Scrap weight: {rec.scrap_weight_kg} kg")
        print(f"Method: {rec.recycling_method}")
        print(f"Recoverable rubber: {rec.recoverable_rubber_kg():.2f} kg")
        print(f"Yield: {rec.recycling_yield_percent()}%")
        print(f"Final product: {rec.final_product_kg():.2f} kg")
        print(f"Energy consumption: {rec.energy_consumption_kwh():.2f} kWh")
        print(f"Transport emissions: {rec.transport_emissions_kg_co2():.3f} kg CO2")
        print(f"Cost savings: ${rec.cost_savings():.2f}")
        print(f"Stats: {rec.stats()}")

if __name__ == "__main__":
    RubberRecycling(0).run()
