"""Native stdlib module: Harvest Cost Calculator
Calculates logging costs, equipment productivity, and stumpage value for timber.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class HarvestSystem(Enum):
    MANUAL = "manual"
    MECHANIZED_FELLER = "mechanized_feller"
    CABLE_YARDING = "cable_yarding"
    HELICOPTER = "helicopter"

@dataclass
class HarvestCostCalculator:
    harvest_system: HarvestSystem
    volume_m3: float
    extraction_distance_m: float
    slope_pct: float
    stumpage_price_m3: float
    equipment_cost_hr: float

    def productivity_m3_hr(self) -> float:
        base = {HarvestSystem.MANUAL: 8, HarvestSystem.MECHANIZED_FELLER: 40, HarvestSystem.CABLE_YARDING: 20, HarvestSystem.HELICOPTER: 15}
        prod = base.get(self.harvest_system, 20)
        if self.slope_pct > 30:
            prod *= 0.7
        if self.extraction_distance_m > 500:
            prod *= 0.85
        return prod

    def harvest_time_hr(self) -> float:
        if self.productivity_m3_hr() == 0:
            return 0.0
        return self.volume_m3 / self.productivity_m3_hr()

    def harvest_cost_m3(self) -> float:
        if self.productivity_m3_hr() == 0:
            return 0.0
        return self.equipment_cost_hr / self.productivity_m3_hr()

    def total_harvest_cost(self) -> float:
        return self.harvest_cost_m3() * self.volume_m3

    def revenue(self) -> float:
        return self.volume_m3 * self.stumpage_price_m3

    def profit(self) -> float:
        return self.revenue() - self.total_harvest_cost()

    def stats(self) -> Dict:
        return {
            "harvest_system": self.harvest_system.value,
            "productivity_m3_hr": round(self.productivity_m3_hr(), 1),
            "harvest_time_hr": round(self.harvest_time_hr(), 1),
            "harvest_cost_m3": round(self.harvest_cost_m3(), 2),
            "total_cost": round(self.total_harvest_cost(), 2),
            "revenue": round(self.revenue(), 2),
            "profit": round(self.profit(), 2),
        }

def run():
    hcc = HarvestCostCalculator(harvest_system=HarvestSystem.MECHANIZED_FELLER, volume_m3=500, extraction_distance_m=300, slope_pct=15, stumpage_price_m3=45, equipment_cost_hr=120)
    print(hcc.stats())

if __name__ == "__main__":
    run()
