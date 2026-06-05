"""Native stdlib module: Carbon Sequestration Calculator
Estimates forest carbon storage, sequestration rates, and offset values.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class ForestType(Enum):
    TROPICAL_RAINFOREST = "tropical_rainforest"
    TEMPERATE_DECIDUOUS = "temperate_deciduous"
    BOREAL_CONIFEROUS = "boreal_coniferous"
    MANGROVE = "mangrove"
    PLANTATION = "plantation"

@dataclass
class CarbonSequestrationCalculator:
    forest_type: ForestType
    area_ha: float
    age_years: float
    biomass_ton_ha: float
    carbon_price_usd_per_ton: float = 10.0

    def carbon_stock_ton_c_ha(self) -> float:
        return self.biomass_ton_ha * 0.5

    def total_carbon_stock_ton(self) -> float:
        return self.carbon_stock_ton_c_ha() * self.area_ha

    def co2_equivalent_ton(self) -> float:
        return self.total_carbon_stock_ton() * (44 / 12)

    def annual_sequestration_ton_c_ha(self) -> float:
        rates = {ForestType.TROPICAL_RAINFOREST: 5.0, ForestType.TEMPERATE_DECIDUOUS: 3.5, ForestType.BOREAL_CONIFEROUS: 2.0, ForestType.MANGROVE: 6.0, ForestType.PLANTATION: 8.0}
        if self.age_years > 50:
            return rates.get(self.forest_type, 3.0) * 0.5
        return rates.get(self.forest_type, 3.0)

    def annual_sequestration_ton_c(self) -> float:
        return self.annual_sequestration_ton_c_ha() * self.area_ha

    def annual_co2_sequestration_ton(self) -> float:
        return self.annual_sequestration_ton_c() * (44 / 12)

    def carbon_credit_value_usd(self) -> float:
        return self.annual_co2_sequestration_ton() * self.carbon_price_usd_per_ton

    def stats(self) -> Dict:
        return {
            "forest_type": self.forest_type.value,
            "area_ha": self.area_ha,
            "carbon_stock_ton": round(self.total_carbon_stock_ton(), 1),
            "co2_equivalent_ton": round(self.co2_equivalent_ton(), 1),
            "annual_sequestration_ton_c": round(self.annual_sequestration_ton_c(), 1),
            "annual_co2_ton": round(self.annual_co2_sequestration_ton(), 1),
            "credit_value_usd": round(self.carbon_credit_value_usd(), 2),
        }

def run():
    csc = CarbonSequestrationCalculator(forest_type=ForestType.TEMPERATE_DECIDUOUS, area_ha=100, age_years=30, biomass_ton_ha=120, carbon_price_usd_per_ton=15)
    print(csc.stats())

if __name__ == "__main__":
    run()
