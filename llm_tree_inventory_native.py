"""Tree Inventory — DBH, height, volume, species, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class Tree:
    species: str
    dbh_cm: float
    height_m: float

class TreeInventory:
    def __init__(self):
        self.trees: List[Tree] = []

    def add_tree(self, t: Tree):
        self.trees.append(t)

    def basal_area(self, t: Tree) -> float:
        return math.pi * (t.dbh_cm / 200) ** 2

    def volume(self, t: Tree) -> float:
        return self.basal_area(t) * t.height_m * 0.5

    def total_basal_area(self) -> float:
        return sum(self.basal_area(t) for t in self.trees)

    def total_volume(self) -> float:
        return sum(self.volume(t) for t in self.trees)

    def species_count(self) -> Dict[str, int]:
        counts = {}
        for t in self.trees:
            counts[t.species] = counts.get(t.species, 0) + 1
        return counts

    def diversity_index(self) -> float:
        n = len(self.trees)
        if n == 0:
            return 0.0
        counts = self.species_count()
        return -sum((c/n) * math.log(c/n) for c in counts.values() if c > 0)

    def stats(self) -> Dict:
        return {"trees": len(self.trees), "basal_area": round(self.total_basal_area(), 3), "volume": round(self.total_volume(), 3), "diversity": round(self.diversity_index(), 3)}

def run():
    ti = TreeInventory()
    ti.add_tree(Tree("Oak", 40, 25))
    ti.add_tree(Tree("Pine", 30, 20))
    ti.add_tree(Tree("Oak", 45, 28))
    print(ti.stats())
    print("Species:", ti.species_count())

if __name__ == "__main__":
    run()
