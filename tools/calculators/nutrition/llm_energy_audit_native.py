"""Native stdlib module: Energy Audit
Calculates energy consumption, costs, and savings potential for buildings.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class EnergyEndUse:
    category: str
    annual_kwh: float
    cost_per_kwh: float
    retrofit_savings_pct: float = 0.0

@dataclass
class EnergyAudit:
    building_name: str
    square_feet: float
    end_uses: List[EnergyEndUse] = field(default_factory=list)

    def total_consumption_kwh(self) -> float:
        return sum(e.annual_kwh for e in self.end_uses)

    def total_cost(self) -> float:
        return sum(e.annual_kwh * e.cost_per_kwh for e in self.end_uses)

    def eui(self) -> float:
        if self.square_feet == 0:
            return 0.0
        return self.total_consumption_kwh() / self.square_feet

    def potential_savings(self) -> float:
        return sum(e.annual_kwh * e.cost_per_kwh * (e.retrofit_savings_pct / 100) for e in self.end_uses)

    def by_category(self) -> Dict[str, float]:
        return {e.category: e.annual_kwh for e in self.end_uses}

    def stats(self) -> Dict:
        return {
            "building": self.building_name,
            "total_kwh": round(self.total_consumption_kwh(), 1),
            "total_cost": round(self.total_cost(), 2),
            "eui_kwh_sqft": round(self.eui(), 2),
            "potential_savings": round(self.potential_savings(), 2),
            "by_category": self.by_category(),
        }

def run():
    ea = EnergyAudit(
        building_name="Office Tower",
        square_feet=50000,
        end_uses=[
            EnergyEndUse("hvac", 250000, 0.12, 15),
            EnergyEndUse("lighting", 80000, 0.12, 30),
            EnergyEndUse("equipment", 120000, 0.12, 10),
            EnergyEndUse("hot_water", 40000, 0.12, 20),
        ]
    )
    print(ea.stats())

if __name__ == "__main__":
    run()
