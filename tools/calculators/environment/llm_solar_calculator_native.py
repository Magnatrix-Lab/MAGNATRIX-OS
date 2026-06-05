"""Native stdlib module: Solar Calculator
Estimates solar panel output, system size, and payback period.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class SolarCalculator:
    system_kw: float
    panel_efficiency_pct: float
    peak_sun_hours: float
    install_cost_per_watt: float
    electricity_rate_per_kwh: float
    annual_degradation_pct: float = 0.5

    def annual_production_kwh(self) -> float:
        return self.system_kw * self.peak_sun_hours * 365 * (self.panel_efficiency_pct / 100)

    def total_install_cost(self) -> float:
        return self.system_kw * 1000 * self.install_cost_per_watt

    def annual_savings(self) -> float:
        return self.annual_production_kwh() * self.electricity_rate_per_kwh

    def simple_payback_years(self) -> float:
        if self.annual_savings() == 0:
            return 0.0
        return self.total_install_cost() / self.annual_savings()

    def production_year(self, year: int) -> float:
        return self.annual_production_kwh() * ((1 - self.annual_degradation_pct / 100) ** year)

    def stats(self) -> Dict[str, float]:
        return {
            "annual_production_kwh": round(self.annual_production_kwh(), 1),
            "total_install_cost": round(self.total_install_cost(), 2),
            "annual_savings": round(self.annual_savings(), 2),
            "payback_years": round(self.simple_payback_years(), 1),
            "production_y1": round(self.annual_production_kwh(), 1),
            "production_y10": round(self.production_year(10), 1),
        }

def run():
    sc = SolarCalculator(system_kw=6, panel_efficiency_pct=20, peak_sun_hours=5.5, install_cost_per_watt=2.8, electricity_rate_per_kwh=0.14)
    print(sc.stats())

if __name__ == "__main__":
    run()
