"""Pattern Generator — tessellation, symmetry, repeat, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class PatternGenerator:
    width: int = 10
    height: int = 10

    def checkerboard(self, a: str = "X", b: str = "O") -> List[str]:
        return [''.join(a if (i+j)%2==0 else b for j in range(self.width)) for i in range(self.height)]

    def stripes(self, direction: str = "horizontal") -> List[str]:
        if direction == "horizontal":
            return [''.join(str(i%2) for _ in range(self.width)) for i in range(self.height)]
        return [''.join(str(i%2) for i in range(self.width)) for _ in range(self.height)]

    def diagonal(self, a: str = "#", b: str = ".") -> List[str]:
        return [''.join(a if (i+j)%3==0 else b for j in range(self.width)) for i in range(self.height)]

    def radial_symmetry(self, points: List[Tuple[int, int]], order: int = 4) -> List[Tuple[int, int]]:
        result = []
        cx, cy = self.width // 2, self.height // 2
        for x, y in points:
            for i in range(order):
                angle = 2 * 3.14159 * i / order
                import math
                dx = x - cx
                dy = y - cy
                rx = int(cx + dx * math.cos(angle) - dy * math.sin(angle))
                ry = int(cy + dx * math.sin(angle) + dy * math.cos(angle))
                result.append((rx, ry))
        return result

    def stats(self) -> Dict:
        return {"width": self.width, "height": self.height, "cells": self.width * self.height}

def run():
    pg = PatternGenerator(8, 8)
    print("Checkerboard:")
    for row in pg.checkerboard():
        print(row)
    print(pg.stats())

if __name__ == "__main__":
    run()
