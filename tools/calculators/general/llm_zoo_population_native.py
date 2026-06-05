"""Zoo Population — studbook, genetic diversity, breeding, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

@dataclass
class Animal:
    id: str
    sex: str
    birth_year: int
    parents: List[str] = field(default_factory=list)

class ZooPopulation:
    def __init__(self):
        self.animals: List[Animal] = []

    def add_animal(self, a: Animal):
        self.animals.append(a)

    def sex_ratio(self) -> Dict[str, int]:
        return {"male": sum(1 for a in self.animals if a.sex == "M"), "female": sum(1 for a in self.animals if a.sex == "F")}

    def breeding_pairs(self) -> List[Tuple[str, str]]:
        males = [a for a in self.animals if a.sex == "M"]
        females = [a for a in self.animals if a.sex == "F"]
        pairs = []
        for m in males:
            for f in females:
                if not set(m.parents) & set(f.parents):
                    pairs.append((m.id, f.id))
        return pairs

    def mean_kinship(self, animal_id: str) -> float:
        a = next((x for x in self.animals if x.id == animal_id), None)
        if not a or not a.parents:
            return 0.0
        return 0.5 * sum(1 for p in a.parents if p) / 2

    def generation_length(self) -> float:
        if not self.animals:
            return 0.0
        return sum(2024 - a.birth_year for a in self.animals) / len(self.animals)

    def stats(self) -> Dict:
        return {"total": len(self.animals), "sex_ratio": self.sex_ratio(), "breeding_pairs": len(self.breeding_pairs())}

def run():
    zp = ZooPopulation()
    zp.add_animal(Animal("A1", "M", 2015, ["A3", "A4"]))
    zp.add_animal(Animal("A2", "F", 2016, ["A5", "A6"]))
    zp.add_animal(Animal("A3", "M", 2010, []))
    zp.add_animal(Animal("A4", "F", 2010, []))
    print(zp.stats())
    print("Breeding pairs:", zp.breeding_pairs())

if __name__ == "__main__":
    run()
