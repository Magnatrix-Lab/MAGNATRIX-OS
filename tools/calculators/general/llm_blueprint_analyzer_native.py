"""Blueprint Analyzer — area, perimeter, room adjacency, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class Room:
    name: str
    x: float
    y: float
    width: float
    height: float

class BlueprintAnalyzer:
    def __init__(self):
        self.rooms: List[Room] = []

    def add_room(self, r: Room):
        self.rooms.append(r)

    def total_area(self) -> float:
        return sum(r.width * r.height for r in self.rooms)

    def room_area(self, name: str) -> float:
        r = next((x for x in self.rooms if x.name == name), None)
        return r.width * r.height if r else 0.0

    def perimeter(self) -> float:
        total = 0.0
        for r in self.rooms:
            total += 2 * (r.width + r.height)
        return total

    def adjacency(self, r1: Room, r2: Room) -> bool:
        x_overlap = max(0, min(r1.x + r1.width, r2.x + r2.width) - max(r1.x, r2.x))
        y_overlap = max(0, min(r1.y + r1.height, r2.y + r2.height) - max(r1.y, r2.y))
        return x_overlap > 0 or y_overlap > 0

    def adjacency_map(self) -> Dict[str, List[str]]:
        adj = {}
        for r1 in self.rooms:
            adj[r1.name] = [r2.name for r2 in self.rooms if r1.name != r2.name and self.adjacency(r1, r2)]
        return adj

    def stats(self) -> Dict:
        return {"rooms": len(self.rooms), "total_area": self.total_area(), "perimeter": self.perimeter()}

def run():
    ba = BlueprintAnalyzer()
    ba.add_room(Room("Living", 0, 0, 5, 4))
    ba.add_room(Room("Kitchen", 5, 0, 3, 4))
    ba.add_room(Room("Bedroom", 0, 4, 4, 4))
    print(ba.stats())
    print("Adjacency:", ba.adjacency_map())

if __name__ == "__main__":
    run()
