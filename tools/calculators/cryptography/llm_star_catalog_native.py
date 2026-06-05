"""Star Catalog — magnitude, coordinates, distance, stellar classification, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class Star:
    name: str
    ra: float
    dec: float
    magnitude: float
    distance_pc: float = 0.0
    spectral_type: str = ""

class StarCatalog:
    def __init__(self):
        self.stars: List[Star] = []

    def add(self, star: Star):
        self.stars.append(star)

    def apparent_to_absolute(self, star: Star) -> float:
        return star.magnitude - 5 * math.log10(star.distance_pc / 10) if star.distance_pc > 0 else star.magnitude

    def absolute_to_apparent(self, abs_mag: float, distance_pc: float) -> float:
        return abs_mag + 5 * math.log10(distance_pc / 10) if distance_pc > 0 else abs_mag

    def angular_distance(self, s1: Star, s2: Star) -> float:
        dra = math.radians(s2.ra - s1.ra)
        d1 = math.radians(90 - s1.dec)
        d2 = math.radians(90 - s2.dec)
        return math.degrees(math.acos(max(-1, min(1, math.cos(d1)*math.cos(d2) + math.sin(d1)*math.sin(d2)*math.cos(dra)))))

    def by_magnitude(self, limit: float = 6.0) -> List[Star]:
        return [s for s in self.stars if s.magnitude <= limit]

    def by_constellation(self, stars: List[Star]) -> Dict[str, List[str]]:
        """Simplified grouping by declination bands."""
        groups = {}
        for s in stars:
            band = f"Dec_{int(s.dec//10)*10}"
            groups.setdefault(band, []).append(s.name)
        return groups

    def stats(self) -> Dict:
        return {"stars": len(self.stars), "avg_mag": sum(s.magnitude for s in self.stars)/len(self.stars) if self.stars else 0}

def run():
    sc = StarCatalog()
    sc.add(Star("Sirius", 101.3, -16.7, -1.46, 2.64, "A1V"))
    sc.add(Star("Betelgeuse", 88.8, 7.4, 0.5, 130, "M1-2"))
    print("Bright:", [s.name for s in sc.by_magnitude(1.0)])
    print("Dist Sirius:", sc.angular_distance(sc.stars[0], sc.stars[1]))
    print(sc.stats())

if __name__ == "__main__":
    run()
