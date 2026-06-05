"""Carbon Sequester Calculator — biomass, forest, soil, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class CarbonSequester:
    tree_biomass_tons: float = 0.0
    soil_carbon_tons: float = 0.0
    area_ha: float = 1.0
    age_years: float = 10.0

    def tree_carbon(self) -> float:
        return self.tree_biomass_tons * 0.5

    def annual_sequestration(self) -> float:
        if self.age_years <= 0:
            return 0.0
        return self.tree_carbon() / self.age_years

    def per_hectare(self) -> float:
        if self.area_ha <= 0:
            return 0.0
        return (self.tree_carbon() + self.soil_carbon_tons) / self.area_ha

    def co2_equivalent(self) -> float:
        return self.tree_carbon() * 3.67

    def offset_cars(self) -> float:
        return self.co2_equivalent() / 4.6

    def stats(self) -> Dict:
        return {"tree_carbon": round(self.tree_carbon(), 1), "annual": round(self.annual_sequestration(), 2), "per_ha": round(self.per_hectare(), 1), "co2_eq": round(self.co2_equivalent(), 1)}

def run():
    cs = CarbonSequester(tree_biomass_tons=100, soil_carbon_tons=50, area_ha=2, age_years=20)
    print(cs.stats())
    print("Offsets cars:", cs.offset_cars())

if __name__ == "__main__":
    run()
