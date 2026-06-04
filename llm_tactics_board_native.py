"""Tactics Board — formations, positions, coverage, spacing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class Player:
    id: str
    x: float
    y: float

class TacticsBoard:
    def __init__(self):
        self.players: List[Player] = []
        self.field_width: float = 100.0
        self.field_height: float = 50.0

    def add_player(self, p: Player):
        self.players.append(p)

    def distance(self, p1: Player, p2: Player) -> float:
        return math.sqrt((p1.x-p2.x)**2 + (p1.y-p2.y)**2)

    def average_spacing(self) -> float:
        if len(self.players) < 2:
            return 0.0
        dists = []
        for i in range(len(self.players)):
            for j in range(i+1, len(self.players)):
                dists.append(self.distance(self.players[i], self.players[j]))
        return sum(dists) / len(dists)

    def formation_compactness(self) -> float:
        if not self.players:
            return 0.0
        xs = [p.x for p in self.players]
        ys = [p.y for p in self.players]
        width = max(xs) - min(xs)
        height = max(ys) - min(ys)
        return 1 - (width * height) / (self.field_width * self.field_height)

    def coverage(self, zones: int = 6) -> Dict[int, int]:
        zone_width = self.field_width / zones
        counts = {}
        for p in self.players:
            z = int(p.x / zone_width)
            counts[z] = counts.get(z, 0) + 1
        return counts

    def stats(self) -> Dict:
        return {"players": len(self.players), "spacing": round(self.average_spacing(), 1), "compactness": round(self.formation_compactness(), 3)}

def run():
    tb = TacticsBoard()
    for i in range(11):
        tb.add_player(Player(f"P{i}", i*8, 25))
    print(tb.stats())
    print("Coverage:", tb.coverage())

if __name__ == "__main__":
    run()
