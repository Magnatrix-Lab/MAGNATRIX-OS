"""Tree Inventory — DBH, height, volume, species, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
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

    def basal_area(self, tree: Tree) -> float:
        r = tree.dbh_cm / 200
        return math.pi * r * r

    def total_basal_area(self) -> float:
        return sum(self.basal_area(t) for t in self.trees)

    def volume(self, tree: Tree, form_factor: float = 0.5) -> float:
        return self.basal_area(tree) * tree.height_m * form_factor

    def total_volume(self) -> float:
        return sum(self.volume(t) for t in self.trees)

    def species_count(self) -> Dict[str, int]:
        counts = {}
        for t in self.trees:
            counts[t.species] = counts.get(t.species, 0) + 1
        return counts

    def avg_dbh(self) -> float:
        return sum(t.dbh_cm for t in self.trees) / len(self.trees) if self.trees else 0.0

    def stats(self) -> Dict:
        return {"trees": len(self.trees), "basal_area": round(self.total_basal_area(), 2), "volume": round(self.total_volume(), 2), "species": len(self.species_count())}

def run():
    ti = TreeInventory()
    ti.add_tree(Tree("Pine", 30, 20))
    ti.add_tree(Tree("Oak", 45, 25))
    ti.add_tree(Tree("Pine", 25, 18))
    print(ti.stats())
    print("Species:", ti.species_count())

if __name__ == "__main__":
    run()
