"""Native stdlib module: Paper Machine Calculator
Calculates paper machine speed, basis weight, and production rates.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class PaperMachineCalculator:
    machine_width_m: float
    machine_speed_m_min: float
    basis_weight_g_m2: float
    trim_width_m: float
    operating_efficiency_pct: float
    moisture_content_pct: float = 8.0

    def dry_end_width_m(self) -> float:
        return self.trim_width_m * 0.95

    def production_rate_ton_hr(self) -> float:
        area_m2_min = self.dry_end_width_m() * self.machine_speed_m_min
        dry_weight_g_m2 = self.basis_weight_g_m2 * (1 - self.moisture_content_pct / 100)
        return (area_m2_min * dry_weight_g_m2 / 1000 / 1000) * 60 * (self.operating_efficiency_pct / 100)

    def production_rate_ton_day(self) -> float:
        return self.production_rate_ton_hr() * 24

    def annual_production_ton(self, operating_days: int = 340) -> float:
        return self.production_rate_ton_day() * operating_days

    def specific_energy_consumption_kwh_ton(self) -> float:
        return 500 + (self.machine_speed_m_min / 1000) * 200

    def fiber_requirement_ton_day(self, yield_pct: float = 50) -> float:
        if yield_pct == 0:
            return 0.0
        return self.production_rate_ton_day() / (yield_pct / 100)

    def water_consumption_m3_ton(self) -> float:
        return 50 - (self.machine_speed_m_min / 100)

    def stats(self) -> Dict:
        return {
            "production_rate_ton_hr": round(self.production_rate_ton_hr(), 2),
            "production_rate_ton_day": round(self.production_rate_ton_day(), 2),
            "annual_production_ton": round(self.annual_production_ton(), 1),
            "specific_energy_kwh_ton": round(self.specific_energy_consumption_kwh_ton(), 1),
            "fiber_requirement_ton_day": round(self.fiber_requirement_ton_day(), 1),
            "water_consumption_m3_ton": round(self.water_consumption_m3_ton(), 1),
        }

def run():
    pmc = PaperMachineCalculator(machine_width_m=8, machine_speed_m_min=1000, basis_weight_g_m2=80, trim_width_m=7.5, operating_efficiency_pct=92, moisture_content_pct=8)
    print(pmc.stats())

if __name__ == "__main__":
    run()
