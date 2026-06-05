"""Tree Inventory — DBH, height, volume, biomass, native, stdlib only."""
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

    def volume(self, t: Tree) -> float:
        """Smalian formula approximation."""
        r = t.dbh_cm / 200
        return math.pi * r ** 2 * t.height_m * 0.5

    def biomass(self, t: Tree) -> float:
        """General allometric equation."""
        return 0.0577 * (t.dbh_cm ** 2) * t.height_m

    def carbon_stock(self, t: Tree) -> float:
        return self.biomass(t) * 0.47

    def basal_area(self, t: Tree) -> float:
        r = t.dbh_cm / 200
        return math.pi * r ** 2

    def total_basal_area(self) -> float:
        return sum(self.basal_area(t) for t in self.trees)

    def total_volume(self) -> float:
        return sum(self.volume(t) for t in self.trees)

    def species_distribution(self) -> Dict[str, int]:
        dist = {}
        for t in self.trees:
            dist[t.species] = dist.get(t.species, 0) + 1
        return dist

    def stats(self) -> Dict:
        return {
            "trees": len(self.trees),
            "total_basal_area": round(self.total_basal_area(), 3),
            "total_volume": round(self.total_volume(), 2),
            "species": self.species_distribution()
        }

def run():
    ti = TreeInventory()
    ti.add_tree(Tree("Oak", 45, 25))
    ti.add_tree(Tree("Pine", 35, 30))
    ti.add_tree(Tree("Oak", 50, 28))
    print(ti.stats())
    for t in ti.trees:
        print(f"{t.species}: carbon={ti.carbon_stock(t):.1f} kg")

if __name__ == "__main__":
    run()
