"""Native stdlib module: Catering Calculator
Calculates food quantities, costs, and service staffing for events.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class ServiceStyle(Enum):
    BUFFET = "buffet"
    PLATED = "plated"
    FAMILY_STYLE = "family_style"
    COCKTAIL = "cocktail"

@dataclass
class MenuItem:
    name: str
    portion_per_person: float
    unit_cost: float

@dataclass
class CateringCalculator:
    event_name: str
    guest_count: int
    service_style: ServiceStyle
    menu_items: List[MenuItem] = field(default_factory=list)
    staff_per_20_guests: float = 1.0

    def total_food_cost(self) -> float:
        return sum(i.portion_per_person * self.guest_count * i.unit_cost for i in self.menu_items)

    def staff_needed(self) -> int:
        return max(1, int((self.guest_count / 20) * self.staff_per_20_guests))

    def cost_per_person(self) -> float:
        if self.guest_count == 0:
            return 0.0
        return self.total_food_cost() / self.guest_count

    def stats(self) -> Dict[str, float]:
        return {
            "guest_count": self.guest_count,
            "total_food_cost": round(self.total_food_cost(), 2),
            "staff_needed": self.staff_needed(),
            "cost_per_person": round(self.cost_per_person(), 2),
            "service_style": self.service_style.value,
        }

def run():
    cc = CateringCalculator(
        event_name="Wedding Reception",
        guest_count=150,
        service_style=ServiceStyle.PLATED,
        menu_items=[
            MenuItem("salad", 0.15, 8.0),
            MenuItem("main protein", 0.25, 25.0),
            MenuItem("side starch", 0.2, 5.0),
            MenuItem("dessert", 0.12, 6.0),
        ],
        staff_per_20_guests=2.5
    )
    print(cc.stats())

if __name__ == "__main__":
    run()
