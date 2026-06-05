"""Feed Formulator — nutrients, ration, cost, digestibility, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class FeedIngredient:
    name: str
    cp_pct: float
    me_mj_kg: float
    cost_per_kg: float
    max_inclusion: float = 1.0

class FeedFormulator:
    def __init__(self):
        self.ingredients: List[FeedIngredient] = []
        self.target_cp: float = 16.0
        self.target_me: float = 12.0

    def add_ingredient(self, i: FeedIngredient):
        self.ingredients.append(i)

    def simple_ration(self, proportions: List[float]) -> Dict:
        if len(proportions) != len(self.ingredients):
            return {}
        total = sum(proportions)
        if total == 0:
            return {}
        cp = sum(p * i.cp_pct for p, i in zip(proportions, self.ingredients)) / total
        me = sum(p * i.me_mj_kg for p, i in zip(proportions, self.ingredients)) / total
        cost = sum(p * i.cost_per_kg for p, i in zip(proportions, self.ingredients)) / total
        return {"cp": cp, "me": me, "cost": cost}

    def meets_target(self, proportions: List[float]) -> bool:
        r = self.simple_ration(proportions)
        if not r:
            return False
        return r["cp"] >= self.target_cp * 0.9 and r["me"] >= self.target_me * 0.9

    def least_cost(self, tolerance: float = 0.1) -> List[float]:
        if not self.ingredients:
            return []
        best = None
        best_cost = float('inf')
        for i in range(100):
            for j in range(100 - i):
                if len(self.ingredients) >= 3:
                    k = 100 - i - j
                    props = [i/100, j/100, k/100]
                else:
                    props = [i/100, (100-i)/100]
                r = self.simple_ration(props)
                if r and self.meets_target(props) and r["cost"] < best_cost:
                    best_cost = r["cost"]
                    best = props
        return best

    def stats(self, proportions: List[float]) -> Dict:
        r = self.simple_ration(proportions)
        return {"ration": r, "meets_target": self.meets_target(proportions)}

def run():
    ff = FeedFormulator()
    ff.add_ingredient(FeedIngredient("Corn", 9, 13.5, 0.3))
    ff.add_ingredient(FeedIngredient("Soymeal", 44, 11, 0.5))
    ff.add_ingredient(FeedIngredient("Wheat", 12, 12, 0.25))
    props = [0.5, 0.3, 0.2]
    print(ff.stats(props))
    print("Least cost:", ff.least_cost())

if __name__ == "__main__":
    run()
