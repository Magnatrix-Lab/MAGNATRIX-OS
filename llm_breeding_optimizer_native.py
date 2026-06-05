"""Breeding Optimizer — pedigree, inbreeding, selection, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

@dataclass
class Animal:
    id: str
    traits: Dict[str, float]
    pedigree: List[str] = field(default_factory=list)

class BreedingOptimizer:
    def __init__(self):
        self.animals: Dict[str, Animal] = {}

    def add_animal(self, a: Animal):
        self.animals[a.id] = a

    def inbreeding_coefficient(self, a1: Animal, a2: Animal) -> float:
        common = set(a1.pedigree) & set(a2.pedigree)
        if not common:
            return 0.0
        return len(common) / max(len(a1.pedigree), len(a2.pedigree), 1)

    def estimated_offspring(self, a1: Animal, a2: Animal) -> Dict[str, float]:
        offspring = {}
        for trait in set(a1.traits) & set(a2.traits):
            offspring[trait] = (a1.traits[trait] + a2.traits[trait]) / 2
        return offspring

    def breeding_value(self, a: Animal) -> float:
        return sum(a.traits.values()) / len(a.traits) if a.traits else 0.0

    def best_match(self, a1: Animal, candidates: List[str], max_inbreeding: float = 0.125) -> Optional[str]:
        valid = []
        for cid in candidates:
            a2 = self.animals.get(cid)
            if a2 and self.inbreeding_coefficient(a1, a2) <= max_inbreeding:
                valid.append((cid, self.breeding_value(a2)))
        return max(valid, key=lambda x: x[1])[0] if valid else None

    def stats(self, a1: Animal, a2: Animal) -> Dict:
        return {
            "inbreeding": round(self.inbreeding_coefficient(a1, a2), 3),
            "estimated_offspring": self.estimated_offspring(a1, a2),
            "bv1": round(self.breeding_value(a1), 2),
            "bv2": round(self.breeding_value(a2), 2)
        }

def run():
    bo = BreedingOptimizer()
    bo.add_animal(Animal("A", {"milk": 30, "growth": 1.2}, ["P1", "P2"]))
    bo.add_animal(Animal("B", {"milk": 28, "growth": 1.1}, ["P3", "P4"]))
    bo.add_animal(Animal("C", {"milk": 32, "growth": 1.3}, ["P1", "P5"]))
    print(bo.stats(bo.animals["A"], bo.animals["B"]))
    print("Best match for A:", bo.best_match(bo.animals["A"], ["B", "C"]))

if __name__ == "__main__":
    run()
