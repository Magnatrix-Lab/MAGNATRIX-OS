"""Native stdlib module: Inflation Calculator
Calculates inflation rates, purchasing power, and real vs nominal values.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class InflationCalculator:
    nominal_value: float
    inflation_rate_pct: float
    years: int
    base_year: int = 2020

    def real_value(self) -> float:
        if self.inflation_rate_pct == 0:
            return self.nominal_value
        return self.nominal_value / ((1 + self.inflation_rate_pct / 100) ** self.years)

    def purchasing_power_loss_pct(self) -> float:
        if self.nominal_value == 0:
            return 0.0
        return ((self.nominal_value - self.real_value()) / self.nominal_value) * 100

    def future_value(self) -> float:
        return self.nominal_value * ((1 + self.inflation_rate_pct / 100) ** self.years)

    def equivalent_future_value(self, target_year: int) -> float:
        years_diff = target_year - self.base_year
        return self.nominal_value * ((1 + self.inflation_rate_pct / 100) ** years_diff)

    def deflation_adjusted(self, deflation_rate_pct: float) -> float:
        return self.nominal_value * ((1 - deflation_rate_pct / 100) ** self.years)

    def cpi_index(self, base_cpi: float = 100) -> float:
        return base_cpi * ((1 + self.inflation_rate_pct / 100) ** self.years)

    def stats(self) -> Dict:
        return {
            "nominal_value": self.nominal_value,
            "inflation_rate_pct": self.inflation_rate_pct,
            "years": self.years,
            "real_value": round(self.real_value(), 2),
            "purchasing_power_loss_pct": round(self.purchasing_power_loss_pct(), 2),
            "future_value": round(self.future_value(), 2),
            "cpi_index": round(self.cpi_index(), 2),
        }

def run():
    ic = InflationCalculator(nominal_value=1000, inflation_rate_pct=3, years=10)
    print(ic.stats())

if __name__ == "__main__":
    run()
