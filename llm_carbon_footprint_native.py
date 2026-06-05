"""Native stdlib module: Carbon Footprint Calculator
Estimates carbon footprint from waste, energy, and transport activities.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class CarbonSource:
    category: str
    amount: float
    unit: str
    emission_factor_kg_per_unit: float

@dataclass
class CarbonFootprintCalculator:
    entity_name: str
    period: str
    sources: List[CarbonSource] = field(default_factory=list)

    def total_emissions_kg(self) -> float:
        return sum(s.amount * s.emission_factor_kg_per_unit for s in self.sources)

    def total_emissions_tons(self) -> float:
        return self.total_emissions_kg() / 1000

    def by_category(self) -> Dict[str, float]:
        totals = {}
        for s in self.sources:
            totals[s.category] = totals.get(s.category, 0) + (s.amount * s.emission_factor_kg_per_unit)
        return totals

    def per_capita_kg(self, people: int) -> float:
        if people == 0:
            return 0.0
        return self.total_emissions_kg() / people

    def offset_trees_needed(self, tree_absorption_kg_per_year: float = 20) -> int:
        if tree_absorption_kg_per_year == 0:
            return 0
        return int(self.total_emissions_kg() / tree_absorption_kg_per_year)

    def stats(self, people: int = 1) -> Dict:
        return {
            "entity": self.entity_name,
            "total_kg": round(self.total_emissions_kg(), 1),
            "total_tons": round(self.total_emissions_tons(), 2),
            "per_capita_kg": round(self.per_capita_kg(people), 1),
            "offset_trees": self.offset_trees_needed(),
            "by_category": {k: round(v, 1) for k, v in self.by_category().items()},
        }

def run():
    cfc = CarbonFootprintCalculator(
        entity_name="Small Office",
        period="2024",
        sources=[
            CarbonSource("electricity", 5000, "kWh", 0.5),
            CarbonSource("natural_gas", 2000, "kWh", 0.2),
            CarbonSource("waste", 1000, "kg", 0.5),
            CarbonSource("commute", 10000, "km", 0.12),
        ]
    )
    print(cfc.stats(people=20))

if __name__ == "__main__":
    run()
