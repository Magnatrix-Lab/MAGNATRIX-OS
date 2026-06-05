"""Native stdlib module: Unemployment Calculator
Calculates unemployment rates, labor force participation, and underemployment.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class UnemploymentCalculator:
    labor_force: int
    employed: int
    underemployed: int = 0
    discouraged_workers: int = 0
    working_age_population: int = 0

    def unemployed(self) -> int:
        return self.labor_force - self.employed

    def unemployment_rate_pct(self) -> float:
        if self.labor_force == 0:
            return 0.0
        return (self.unemployed() / self.labor_force) * 100

    def labor_force_participation_rate_pct(self) -> float:
        if self.working_age_population == 0:
            return 0.0
        return (self.labor_force / self.working_age_population) * 100

    def underemployment_rate_pct(self) -> float:
        if self.labor_force == 0:
            return 0.0
        return (self.underemployed / self.labor_force) * 100

    def employment_population_ratio_pct(self) -> float:
        if self.working_age_population == 0:
            return 0.0
        return (self.employed / self.working_age_population) * 100

    def true_unemployment_rate_pct(self) -> float:
        expanded_labor_force = self.labor_force + self.discouraged_workers
        if expanded_labor_force == 0:
            return 0.0
        return ((self.unemployed() + self.discouraged_workers) / expanded_labor_force) * 100

    def stats(self) -> Dict:
        return {
            "labor_force": self.labor_force,
            "employed": self.employed,
            "unemployed": self.unemployed(),
            "unemployment_rate_pct": round(self.unemployment_rate_pct(), 2),
            "labor_force_participation_pct": round(self.labor_force_participation_rate_pct(), 2),
            "underemployment_rate_pct": round(self.underemployment_rate_pct(), 2),
            "employment_population_ratio_pct": round(self.employment_population_ratio_pct(), 2),
            "true_unemployment_pct": round(self.true_unemployment_rate_pct(), 2),
        }

def run():
    uc = UnemploymentCalculator(labor_force=160000000, employed=152000000, underemployed=8000000, discouraged_workers=4000000, working_age_population=260000000)
    print(uc.stats())

if __name__ == "__main__":
    run()
