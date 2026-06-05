"""Native stdlib module: Cheese Maker
Calculates milk volume, culture dosage, rennet, and aging parameters for cheese batches.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class MilkType(Enum):
    COW = "cow"
    GOAT = "goat"
    SHEEP = "sheep"
    BUFFALO = "buffalo"

@dataclass
class CheeseMaker:
    cheese_name: str
    milk_liters: float
    milk_type: MilkType
    culture_dosage_ml_per_l: float = 0.5
    rennet_ml_per_l: float = 0.03
    salt_pct: float = 2.0
    aging_days: int = 30

    def culture_total_ml(self) -> float:
        return self.milk_liters * self.culture_dosage_ml_per_l

    def rennet_total_ml(self) -> float:
        return self.milk_liters * self.rennet_ml_per_l

    def salt_g(self) -> float:
        return (self.milk_liters * 1.03 * 1000) * (self.salt_pct / 100)

    def estimated_yield_kg(self) -> float:
        yields = {MilkType.COW: 0.10, MilkType.GOAT: 0.09, MilkType.SHEEP: 0.14, MilkType.BUFFALO: 0.18}
        return self.milk_liters * yields.get(self.milk_type, 0.10)

    def stats(self) -> Dict[str, float]:
        return {
            "culture_ml": round(self.culture_total_ml(), 2),
            "rennet_ml": round(self.rennet_total_ml(), 2),
            "salt_g": round(self.salt_g(), 1),
            "yield_kg": round(self.estimated_yield_kg(), 2),
            "aging_days": self.aging_days,
        }

def run():
    cm = CheeseMaker(cheese_name="Cheddar", milk_liters=100, milk_type=MilkType.COW, aging_days=90)
    print(cm.stats())

if __name__ == "__main__":
    run()
