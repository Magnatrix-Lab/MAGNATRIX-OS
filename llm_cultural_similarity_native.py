"""Cultural Similarity — traits, distance, phylogeny, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

@dataclass
class CulturalSimilarity:
    cultures: Dict[str, Set[str]] = field(default_factory=dict)
    """culture -> set of traits"""

    def add_culture(self, name: str, traits: Set[str]):
        self.cultures[name] = traits

    def jaccard(self, a: str, b: str) -> float:
        t1 = self.cultures.get(a, set())
        t2 = self.cultures.get(b, set())
        inter = len(t1 & t2)
        union = len(t1 | t2)
        return inter / union if union > 0 else 0.0

    def distance_matrix(self) -> Dict[Tuple[str, str], float]:
        names = list(self.cultures.keys())
        return {(a, b): 1 - self.jaccard(a, b) for a in names for b in names if a < b}

    def nearest_neighbor(self, culture: str) -> Optional[str]:
        others = [c for c in self.cultures if c != culture]
        if not others:
            return None
        return min(others, key=lambda c: 1 - self.jaccard(culture, c))

    def shared_traits(self, a: str, b: str) -> Set[str]:
        return self.cultures.get(a, set()) & self.cultures.get(b, set())

    def stats(self) -> Dict:
        return {"cultures": len(self.cultures), "avg_traits": sum(len(t) for t in self.cultures.values()) / len(self.cultures) if self.cultures else 0}

def run():
    cs = CulturalSimilarity()
    cs.add_culture("A", {"pottery", "agriculture", "metallurgy"})
    cs.add_culture("B", {"pottery", "agriculture", "fishing"})
    cs.add_culture("C", {"hunting", "nomadic", "shamanism"})
    print("Jaccard A-B:", cs.jaccard("A", "B"))
    print("Nearest to A:", cs.nearest_neighbor("A"))
    print(cs.stats())

if __name__ == "__main__":
    run()
