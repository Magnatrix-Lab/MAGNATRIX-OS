"""Constellation Mapper — asterism, boundaries, star connections, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
import math

@dataclass
class ConstellationMapper:
    stars: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    """name -> (ra, dec)"""
    connections: Dict[str, List[Tuple[str, str]]] = field(default_factory=dict)
    """constellation -> [(star1, star2)]"""

    def add_star(self, name: str, ra: float, dec: float):
        self.stars[name] = (ra, dec)

    def connect(self, constellation: str, s1: str, s2: str):
        self.connections.setdefault(constellation, []).append((s1, s2))

    def angular_distance(self, s1: str, s2: str) -> float:
        a = self.stars.get(s1)
        b = self.stars.get(s2)
        if not a or not b:
            return float('inf')
        dra = math.radians(b[0] - a[0])
        d1 = math.radians(90 - a[1])
        d2 = math.radians(90 - b[1])
        return math.degrees(math.acos(max(-1, min(1, math.cos(d1)*math.cos(d2) + math.sin(d1)*math.sin(d2)*math.cos(dra)))))

    def bounding_box(self, constellation: str) -> Optional[Tuple[float, float, float, float]]:
        stars = set()
        for s1, s2 in self.connections.get(constellation, []):
            stars.add(s1); stars.add(s2)
        if not stars:
            return None
        ras = [self.stars[s][0] for s in stars if s in self.stars]
        decs = [self.stars[s][1] for s in stars if s in self.stars]
        return (min(ras), max(ras), min(decs), max(decs)) if ras else None

    def stats(self) -> Dict:
        return {"stars": len(self.stars), "constellations": len(self.connections)}

def run():
    cm = ConstellationMapper()
    cm.add_star("A", 0, 0); cm.add_star("B", 1, 1); cm.add_star("C", 2, 0)
    cm.connect("Test", "A", "B"); cm.connect("Test", "B", "C")
    print("Dist:", cm.angular_distance("A", "B"))
    print("BBox:", cm.bounding_box("Test"))
    print(cm.stats())

if __name__ == "__main__":
    run()
