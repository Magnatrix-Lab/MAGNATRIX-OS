"""Procedural Terrain Generator — noise-based heightmaps, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import random
import math

class NoiseType(Enum):
    VALUE = auto()
    PERLIN = auto()
    SIMPLEX = auto()

class ProceduralTerrain:
    def __init__(self, width: int = 64, height: int = 64, seed: int = 42):
        self.width = width
        self.height = height
        self.seed = seed
        random.seed(seed)
        self.heightmap: List[List[float]] = [[0.0 for _ in range(width)] for _ in range(height)]
        self.gradients: Dict[Tuple[int, int], Tuple[float, float]] = {}

    def _random_gradient(self, x: int, y: int) -> Tuple[float, float]:
        key = (x + self.seed * 1000, y + self.seed * 2000)
        random.seed(hash(key) % (2**31))
        angle = random.random() * 2 * math.pi
        return (math.cos(angle), math.sin(angle))

    def _dot_gradient(self, x: int, y: int, dx: float, dy: float) -> float:
        g = self._random_gradient(x, y)
        return g[0] * dx + g[1] * dy

    def _perlin(self, x: float, y: float) -> float:
        x0, y0 = int(x), int(y)
        x1, y1 = x0 + 1, y0 + 1
        sx, sy = x - x0, y - y0
        n0 = self._dot_gradient(x0, y0, sx, sy)
        n1 = self._dot_gradient(x1, y0, sx - 1, sy)
        ix0 = n0 + (n1 - n0) * sx * sx * (3 - 2 * sx)
        n2 = self._dot_gradient(x0, y1, sx, sy - 1)
        n3 = self._dot_gradient(x1, y1, sx - 1, sy - 1)
        ix1 = n2 + (n3 - n2) * sx * sx * (3 - 2 * sx)
        return ix0 + (ix1 - ix0) * sy * sy * (3 - 2 * sy)

    def generate(self, octaves: int = 4, persistence: float = 0.5, scale: float = 0.1) -> List[List[float]]:
        for y in range(self.height):
            for x in range(self.width):
                total = 0.0
                amplitude = 1.0
                frequency = scale
                max_val = 0.0
                for _ in range(octaves):
                    total += self._perlin(x * frequency, y * frequency) * amplitude
                    max_val += amplitude
                    amplitude *= persistence
                    frequency *= 2
                self.heightmap[y][x] = total / max_val
        return self.heightmap

    def get_height(self, x: int, y: int) -> float:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.heightmap[y][x]
        return 0.0

    def erode(self, iterations: int = 10) -> List[List[float]]:
        for _ in range(iterations):
            new_map = [row[:] for row in self.heightmap]
            for y in range(1, self.height - 1):
                for x in range(1, self.width - 1):
                    neighbors = [self.heightmap[y-1][x], self.heightmap[y+1][x], self.heightmap[y][x-1], self.heightmap[y][x+1]]
                    new_map[y][x] = (self.heightmap[y][x] + sum(neighbors)) / 5
            self.heightmap = new_map
        return self.heightmap

    def stats(self) -> Dict:
        flat = [h for row in self.heightmap for h in row]
        return {"width": self.width, "height": self.height, "min": min(flat) if flat else 0, "max": max(flat) if flat else 0, "avg": sum(flat) / len(flat) if flat else 0}

def run():
    terrain = ProceduralTerrain(32, 32, seed=123)
    terrain.generate(octaves=4, scale=0.1)
    terrain.erode(5)
    print(terrain.stats())

if __name__ == "__main__":
    run()
