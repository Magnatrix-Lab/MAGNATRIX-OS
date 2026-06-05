"""Pollinator Mapper — foraging, range, overlap, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
import math

@dataclass
class Pollinator:
    species: str
    x: float
    y: float
    foraging_range: float

class PollinatorMapper:
    def __init__(self):
        self.pollinators: List[Pollinator] = []
        self.plants: List[Tuple[str, float, float]] = []

    def add_pollinator(self, p: Pollinator):
        self.pollinators.append(p)

    def add_plant(self, name: str, x: float, y: float):
        self.plants.append((name, x, y))

    def reachable_plants(self, pollinator: Pollinator) -> List[str]:
        reachable = []
        for name, px, py in self.plants:
            d = math.sqrt((pollinator.x - px)**2 + (pollinator.y - py)**2)
            if d <= pollinator.foraging_range:
                reachable.append(name)
        return reachable

    def overlap(self, p1: Pollinator, p2: Pollinator) -> float:
        d = math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)
        if d >= p1.foraging_range + p2.foraging_range:
            return 0.0
        r1, r2 = p1.foraging_range, p2.foraging_range
        if d <= abs(r1 - r2):
            return math.pi * min(r1, r2)**2
        a = (r1**2 - r2**2 + d**2) / (2 * d)
        h = math.sqrt(max(0, r1**2 - a**2))
        return r1**2 * math.acos((r1**2 + d**2 - r2**2) / (2 * r1 * d)) + r2**2 * math.acos((r2**2 + d**2 - r1**2) / (2 * r2 * d)) - 2 * h * d

    def stats(self) -> Dict:
        return {"pollinators": len(self.pollinators), "plants": len(self.plants)}

def run():
    pm = PollinatorMapper()
    pm.add_pollinator(Pollinator("Bee", 0, 0, 100))
    pm.add_pollinator(Pollinator("Butterfly", 50, 50, 80))
    pm.add_plant("Rose", 30, 30)
    pm.add_plant("Lily", 150, 150)
    print(pm.stats())
    print("Bee reach:", pm.reachable_plants(pm.pollinators[0]))

if __name__ == "__main__":
    run()
