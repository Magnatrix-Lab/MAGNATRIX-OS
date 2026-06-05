"""Fabric Optimizer — nesting, yield, grain, markers, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class Piece:
    name: str
    width: float
    height: float
    quantity: int = 1

class FabricOptimizer:
    def __init__(self):
        self.pieces: List[Piece] = []
        self.fabric_width: float = 150.0

    def add_piece(self, p: Piece):
        self.pieces.append(p)

    def total_area(self) -> float:
        return sum(p.width * p.height * p.quantity for p in self.pieces)

    def fabric_needed(self) -> float:
        if not self.pieces:
            return 0.0
        total_width = sum(p.width * p.quantity for p in self.pieces)
        return total_width / self.fabric_width * max(p.height for p in self.pieces)

    def yield_pct(self) -> float:
        used = self.total_area()
        total = self.fabric_needed() * self.fabric_width
        return used / total if total > 0 else 0.0

    def layout_simple(self) -> List[Dict]:
        placements = []
        x = 0.0
        y = 0.0
        max_h = 0.0
        for p in self.pieces:
            for _ in range(p.quantity):
                if x + p.width > self.fabric_width:
                    x = 0
                    y += max_h
                    max_h = 0
                placements.append({"name": p.name, "x": x, "y": y, "w": p.width, "h": p.height})
                x += p.width
                max_h = max(max_h, p.height)
        return placements

    def stats(self) -> Dict:
        return {"pieces": len(self.pieces), "yield": round(self.yield_pct(), 3), "fabric_needed": round(self.fabric_needed(), 1)}

def run():
    fo = FabricOptimizer()
    fo.add_piece(Piece("front", 30, 40, 2))
    fo.add_piece(Piece("back", 30, 40, 2))
    fo.add_piece(Piece("sleeve", 20, 50, 2))
    print(fo.stats())
    print("Layout:", fo.layout_simple()[:3])

if __name__ == "__main__":
    run()
