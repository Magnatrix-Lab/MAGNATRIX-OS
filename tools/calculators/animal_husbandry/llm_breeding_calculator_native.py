"""Breeding Calculator — pedigree, inbreeding coefficient, COI, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

@dataclass
class Animal:
    id: str
    sire: Optional[str] = None
    dam: Optional[str] = None

class BreedingCalculator:
    def __init__(self):
        self.animals: Dict[str, Animal] = {}

    def add_animal(self, a: Animal):
        self.animals[a.id] = a

    def ancestors(self, animal_id: str, generations: int = 3) -> Set[str]:
        result = set()
        current = [animal_id]
        for _ in range(generations):
            next_gen = []
            for aid in current:
                a = self.animals.get(aid)
                if a:
                    if a.sire:
                        result.add(a.sire)
                        next_gen.append(a.sire)
                    if a.dam:
                        result.add(a.dam)
                        next_gen.append(a.dam)
            current = next_gen
        return result

    def coi(self, animal_id: str) -> float:
        a = self.animals.get(animal_id)
        if not a or not a.sire or not a.dam:
            return 0.0
        sire_anc = self.ancestors(a.sire, 5)
        dam_anc = self.ancestors(a.dam, 5)
        common = sire_anc & dam_anc
        if not common:
            return 0.0
        return 0.5 ** len(common)

    def pedigree_depth(self, animal_id: str) -> int:
        a = self.animals.get(animal_id)
        if not a or not a.sire or not a.dam:
            return 0
        return 1 + max(self.pedigree_depth(a.sire), self.pedigree_depth(a.dam))

    def stats(self, animal_id: str) -> Dict:
        return {"coi": round(self.coi(animal_id), 4), "pedigree_depth": self.pedigree_depth(animal_id), "ancestors": len(self.ancestors(animal_id))}

def run():
    bc = BreedingCalculator()
    bc.add_animal(Animal("A"))
    bc.add_animal(Animal("B"))
    bc.add_animal(Animal("C", "A", "B"))
    bc.add_animal(Animal("D", "A", "B"))
    bc.add_animal(Animal("E", "C", "D"))
    print(bc.stats("E"))

if __name__ == "__main__":
    run()
