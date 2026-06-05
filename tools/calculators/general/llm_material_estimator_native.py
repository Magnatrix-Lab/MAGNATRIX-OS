"""Material Estimator — quantity takeoff, waste factor, cost, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class MaterialEstimator:
    items: List[Dict] = field(default_factory=list)
    """Each: {name, quantity, unit_cost, waste_factor}"""

    def add_item(self, name: str, qty: float, unit_cost: float, waste: float = 0.1):
        self.items.append({"name": name, "quantity": qty, "unit_cost": unit_cost, "waste_factor": waste})

    def total_cost(self) -> float:
        return sum(i["quantity"] * (1 + i["waste_factor"]) * i["unit_cost"] for i in self.items)

    def total_quantity(self, name: str) -> float:
        return sum(i["quantity"] * (1 + i["waste_factor"]) for i in self.items if i["name"] == name)

    def by_category(self) -> Dict[str, float]:
        cats = {}
        for i in self.items:
            cats[i["name"]] = cats.get(i["name"], 0) + i["quantity"] * (1 + i["waste_factor"]) * i["unit_cost"]
        return cats

    def stats(self) -> Dict:
        return {"items": len(self.items), "total_cost": round(self.total_cost(), 2)}

def run():
    me = MaterialEstimator()
    me.add_item("Concrete", 10, 100, 0.05)
    me.add_item("Steel", 5, 500, 0.1)
    me.add_item("Concrete", 5, 100, 0.05)
    print(me.stats())
    print("By category:", me.by_category())

if __name__ == "__main__":
    run()
