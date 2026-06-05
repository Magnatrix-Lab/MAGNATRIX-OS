"""Native stdlib module: Mine Drainage Calculator
Calculates dewatering rates, pump capacities, and inflow estimates for mines.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class AquiferType(Enum):
    CONFINED = "confined"
    UNCONFINED = "unconfined"
    FRACTURED = "fractured"
    KARST = "karst"

@dataclass
class MineDrainageCalculator:
    mine_depth_m: float
    aquifer_type: AquiferType
    hydraulic_conductivity_m_d: float
    aquifer_thickness_m: float
    drawdown_m: float
    influence_radius_m: float

    def transmissivity_m2_d(self) -> float:
        return self.hydraulic_conductivity_m_d * self.aquifer_thickness_m

    def inflow_rate_m3_d(self) -> float:
        if self.influence_radius_m == 0 or self.drawdown_m == 0:
            return 0.0
        t = self.transmissivity_m2_d()
        if self.aquifer_type == AquiferType.CONFINED:
            return (2 * math.pi * t * self.drawdown_m) / math.log(self.influence_radius_m / 0.1)
        else:
            return (math.pi * self.hydraulic_conductivity_m_d * (self.aquifer_thickness_m**2 - (self.aquifer_thickness_m - self.drawdown_m)**2)) / math.log(self.influence_radius_m / 0.1)

    def pump_capacity_m3_h(self) -> float:
        if self.inflow_rate_m3_d() == 0:
            return 0.0
        return self.inflow_rate_m3_d() / 24

    def pump_head_m(self) -> float:
        return self.mine_depth_m + 20

    def pump_power_kw(self, efficiency_pct: float = 75) -> float:
        if efficiency_pct == 0:
            return 0.0
        q = self.pump_capacity_m3_h() / 3600
        h = self.pump_head_m()
        rho = 1000
        g = 9.81
        return (rho * g * q * h) / (efficiency_pct / 100) / 1000

    def annual_water_volume_m3(self) -> float:
        return self.inflow_rate_m3_d() * 365

    def stats(self) -> Dict:
        return {
            "aquifer": self.aquifer_type.value,
            "transmissivity_m2_d": round(self.transmissivity_m2_d(), 2),
            "inflow_m3_d": round(self.inflow_rate_m3_d(), 1),
            "pump_capacity_m3_h": round(self.pump_capacity_m3_h(), 1),
            "pump_head_m": self.pump_head_m(),
            "pump_power_kw": round(self.pump_power_kw(), 1),
            "annual_water_m3": round(self.annual_water_volume_m3(), 1),
        }

def run():
    import math
    mdc = MineDrainageCalculator(mine_depth_m=200, aquifer_type=AquiferType.CONFINED, hydraulic_conductivity_m_d=5, aquifer_thickness_m=30, drawdown_m=50, influence_radius_m=2000)
    print(mdc.stats())

if __name__ == "__main__":
    run()
