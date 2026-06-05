"""Public Health Modeler — incidence, prevalence, DALY, intervention, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class PublicHealthModeler:
    population: float = 100000.0
    cases: float = 1000.0
    deaths: float = 50.0
    disability_weight: float = 0.3
    average_duration_years: float = 5.0

    def incidence_rate(self) -> float:
        return self.cases / self.population * 100000

    def prevalence_rate(self) -> float:
        return (self.cases * self.average_duration_years) / self.population * 100000

    def case_fatality_rate(self) -> float:
        return self.deaths / self.cases if self.cases > 0 else 0.0

    def dalys(self) -> float:
        yll = self.deaths * self.average_duration_years
        yld = (self.cases - self.deaths) * self.disability_weight * self.average_duration_years
        return yll + yld

    def intervention_impact(self, coverage: float, efficacy: float) -> float:
        return self.dalys() * coverage * efficacy

    def cost_per_daly_averted(self, intervention_cost: float, coverage: float, efficacy: float) -> float:
        averted = self.intervention_impact(coverage, efficacy)
        return intervention_cost / averted if averted > 0 else float('inf')

    def stats(self) -> Dict:
        return {"incidence": round(self.incidence_rate(), 1), "prevalence": round(self.prevalence_rate(), 1), "cfr": round(self.case_fatality_rate(), 3), "dalys": round(self.dalys(), 0)}

def run():
    phm = PublicHealthModeler(cases=5000, deaths=200, disability_weight=0.4, average_duration_years=10)
    print(phm.stats())
    print("DALYs averted:", phm.intervention_impact(0.8, 0.6))
    print("Cost/DALY:", phm.cost_per_daly_averted(1000000, 0.8, 0.6))

if __name__ == "__main__":
    run()
