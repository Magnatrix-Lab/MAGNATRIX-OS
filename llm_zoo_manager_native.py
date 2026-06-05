"""Zoo Manager — enclosures, diets, welfare, enrichment, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class Enclosure:
    id: str
    area_sqm: float
    species: List[str] = field(default_factory=list)
    capacity: int = 5

@dataclass
class AnimalRecord:
    id: str
    species: str
    enclosure: str
    diet: str
    welfare_score: float = 5.0

class ZooManager:
    def __init__(self):
        self.enclosures: Dict[str, Enclosure] = {}
        self.animals: Dict[str, AnimalRecord] = {}

    def add_enclosure(self, e: Enclosure):
        self.enclosures[e.id] = e

    def add_animal(self, a: AnimalRecord):
        self.animals[a.id] = a

    def occupancy(self, enc_id: str) -> float:
        count = sum(1 for a in self.animals.values() if a.enclosure == enc_id)
        cap = self.enclosures.get(enc_id, Enclosure("", 0)).capacity
        return count / cap if cap > 0 else 0.0

    def welfare_avg(self) -> float:
        if not self.animals:
            return 0.0
        return sum(a.welfare_score for a in self.animals.values()) / len(self.animals)

    def enrichment_needed(self) -> List[str]:
        return [a.id for a in self.animals.values() if a.welfare_score < 4]

    def diet_summary(self) -> Dict[str, int]:
        summary = {}
        for a in self.animals.values():
            summary[a.diet] = summary.get(a.diet, 0) + 1
        return summary

    def stats(self) -> Dict:
        return {"animals": len(self.animals), "enclosures": len(self.enclosures), "welfare": round(self.welfare_avg(), 2)}

def run():
    zm = ZooManager()
    zm.add_enclosure(Enclosure("E1", 500, ["lion"], 4))
    zm.add_animal(AnimalRecord("L1", "lion", "E1", "carnivore", 7))
    zm.add_animal(AnimalRecord("L2", "lion", "E1", "carnivore", 6))
    print(zm.stats())
    print("Occupancy E1:", zm.occupancy("E1"))
    print("Diet summary:", zm.diet_summary())

if __name__ == "__main__":
    run()
