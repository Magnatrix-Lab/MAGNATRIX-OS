"""Biodiversity Index — Shannon, Simpson, evenness, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class BiodiversityIndex:
    species_counts: Dict[str, int] = field(default_factory=dict)

    def add_species(self, name: str, count: int):
        self.species_counts[name] = self.species_counts.get(name, 0) + count

    def total_individuals(self) -> int:
        return sum(self.species_counts.values())

    def shannon(self) -> float:
        n = self.total_individuals()
        if n == 0:
            return 0.0
        h = 0.0
        for count in self.species_counts.values():
            p = count / n
            if p > 0:
                h -= p * math.log(p)
        return h

    def simpson(self) -> float:
        n = self.total_individuals()
        if n == 0 or n == 1:
            return 0.0
        return 1 - sum(c * (c - 1) for c in self.species_counts.values()) / (n * (n - 1))

    def evenness(self) -> float:
        s = len(self.species_counts)
        h = self.shannon()
        return h / math.log(s) if s > 1 else 0.0

    def richness(self) -> int:
        return len(self.species_counts)

    def stats(self) -> Dict:
        return {
            "richness": self.richness(),
            "shannon": round(self.shannon(), 3),
            "simpson": round(self.simpson(), 3),
            "evenness": round(self.evenness(), 3),
            "individuals": self.total_individuals()
        }

def run():
    bi = BiodiversityIndex()
    bi.add_species("Oak", 50)
    bi.add_species("Pine", 30)
    bi.add_species("Birch", 20)
    bi.add_species("Maple", 10)
    print(bi.stats())

if __name__ == "__main__":
    run()
