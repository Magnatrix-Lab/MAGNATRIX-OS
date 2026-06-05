"""Biodiversity Indexer — Shannon, Simpson, evenness, richness, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class BiodiversityIndexer:
    species_counts: Dict[str, int] = field(default_factory=dict)

    def add_species(self, name: str, count: int):
        self.species_counts[name] = self.species_counts.get(name, 0) + count

    def richness(self) -> int:
        return len(self.species_counts)

    def total_individuals(self) -> int:
        return sum(self.species_counts.values())

    def shannon_index(self) -> float:
        n = self.total_individuals()
        if n == 0:
            return 0.0
        return -sum((c/n) * math.log(c/n) for c in self.species_counts.values() if c > 0)

    def simpson_index(self) -> float:
        n = self.total_individuals()
        if n == 0:
            return 0.0
        return 1 - sum((c/n)**2 for c in self.species_counts.values())

    def evenness(self) -> float:
        h = self.shannon_index()
        s = self.richness()
        return h / math.log(s) if s > 1 else 0.0

    def stats(self) -> Dict:
        return {"richness": self.richness(), "shannon": round(self.shannon_index(), 3), "simpson": round(self.simpson_index(), 3), "evenness": round(self.evenness(), 3)}

def run():
    bi = BiodiversityIndexer()
    bi.add_species("Oak", 50)
    bi.add_species("Pine", 30)
    bi.add_species("Birch", 20)
    print(bi.stats())

if __name__ == "__main__":
    run()
