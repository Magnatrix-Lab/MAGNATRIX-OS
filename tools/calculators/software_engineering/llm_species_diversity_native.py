"""Species Diversity — Shannon, Simpson, evenness, richness, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class SpeciesDiversity:
    counts: Dict[str, int] = field(default_factory=dict)
    """species -> count"""

    def total_individuals(self) -> int:
        return sum(self.counts.values())

    def richness(self) -> int:
        return len(self.counts)

    def shannon_index(self) -> float:
        n = self.total_individuals()
        if n == 0:
            return 0.0
        h = 0.0
        for count in self.counts.values():
            p = count / n
            h += p * math.log(p)
        return -h

    def simpson_index(self) -> float:
        n = self.total_individuals()
        if n == 0:
            return 0.0
        return sum((c / n) ** 2 for c in self.counts.values())

    def evenness(self) -> float:
        s = self.richness()
        h = self.shannon_index()
        return h / math.log(s) if s > 1 else 0.0

    def dominance(self) -> float:
        if not self.counts:
            return 0.0
        return max(self.counts.values()) / self.total_individuals()

    def stats(self) -> Dict:
        return {"richness": self.richness(), "shannon": round(self.shannon_index(), 3), "simpson": round(self.simpson_index(), 3), "evenness": round(self.evenness(), 3)}

def run():
    sd = SpeciesDiversity({"Oak": 10, "Pine": 8, "Maple": 5, "Birch": 2})
    print(sd.stats())
    print("Dominance:", sd.dominance())

if __name__ == "__main__":
    run()
