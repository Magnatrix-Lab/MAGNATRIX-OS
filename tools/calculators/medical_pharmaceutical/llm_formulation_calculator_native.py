"""Native stdlib module: Formulation Calculator
Calculates tablet composition, excipient ratios, and batch scaling.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Excipient:
    name: str
    weight_mg: float
    function: str

@dataclass
class FormulationCalculator:
    drug_name: str
    active_ingredient_mg: float
    tablet_weight_mg: float
    excipients: List[Excipient] = field(default_factory=list)
    batch_size: int = 1000

    def total_excipient_weight_mg(self) -> float:
        return sum(e.weight_mg for e in self.excipients)

    def total_tablet_weight_mg(self) -> float:
        return self.active_ingredient_mg + self.total_excipient_weight_mg()

    def active_pct(self) -> float:
        if self.total_tablet_weight_mg() == 0:
            return 0.0
        return (self.active_ingredient_mg / self.total_tablet_weight_mg()) * 100

    def excipient_pct(self) -> float:
        return 100 - self.active_pct()

    def batch_active_g(self) -> float:
        return (self.active_ingredient_mg * self.batch_size) / 1000

    def batch_total_weight_kg(self) -> float:
        return (self.total_tablet_weight_mg() * self.batch_size) / 1_000_000

    def by_function(self) -> Dict[str, float]:
        totals = {}
        for e in self.excipients:
            totals[e.function] = totals.get(e.function, 0) + e.weight_mg
        return totals

    def stats(self) -> Dict:
        return {
            "drug": self.drug_name,
            "active_mg": self.active_ingredient_mg,
            "tablet_weight_mg": round(self.total_tablet_weight_mg(), 1),
            "active_pct": round(self.active_pct(), 2),
            "batch_size": self.batch_size,
            "batch_active_g": round(self.batch_active_g(), 2),
            "batch_total_kg": round(self.batch_total_weight_kg(), 3),
            "by_function": self.by_function(),
        }

def run():
    fc = FormulationCalculator(
        drug_name="Paracetamol-500",
        active_ingredient_mg=500,
        tablet_weight_mg=650,
        excipients=[
            Excipient("Microcrystalline cellulose", 100, "filler"),
            Excipient("Povidone", 25, "binder"),
            Excipient("Magnesium stearate", 10, "lubricant"),
            Excipient("Starch", 15, "disintegrant"),
        ],
        batch_size=10000
    )
    print(fc.stats())

if __name__ == "__main__":
    run()
