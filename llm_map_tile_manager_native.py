"""Map Tile Manager — tile indexing, LOD, caching, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum, auto
import math

@dataclass
class Tile:
    x: int
    y: int
    z: int
    data: Optional[bytes] = None

class MapTileManager:
    def __init__(self, max_cache: int = 100):
        self.max_cache = max_cache
        self.cache: Dict[str, Tile] = {}
        self.lru_order: List[str] = []
        self.stats_data: Dict = {"hits": 0, "misses": 0, "evictions": 0}

    def _key(self, x: int, y: int, z: int) -> str:
        return f"{z}/{x}/{y}"

    def latlon_to_tile(self, lat: float, lon: float, zoom: int) -> Tuple[int, int]:
        lat_rad = math.radians(lat)
        n = 2 ** zoom
        x = int((lon + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return x, y

    def tile_to_latlon(self, x: int, y: int, z: int) -> Tuple[float, float]:
        n = 2 ** z
        lon = x / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        lat = math.degrees(lat_rad)
        return lat, lon

    def get_tile(self, x: int, y: int, z: int) -> Optional[Tile]:
        key = self._key(x, y, z)
        if key in self.cache:
            self.stats_data["hits"] += 1
            self.lru_order.remove(key)
            self.lru_order.append(key)
            return self.cache[key]
        self.stats_data["misses"] += 1
        return None

    def put_tile(self, tile: Tile):
        key = self._key(tile.x, tile.y, tile.z)
        if key in self.cache:
            self.lru_order.remove(key)
        elif len(self.cache) >= self.max_cache:
            oldest = self.lru_order.pop(0)
            del self.cache[oldest]
            self.stats_data["evictions"] += 1
        self.cache[key] = tile
        self.lru_order.append(key)

    def get_neighbors(self, x: int, y: int, z: int) -> List[str]:
        neighbors = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                n = 2 ** z
                if 0 <= nx < n and 0 <= ny < n:
                    neighbors.append(self._key(nx, ny, z))
        return neighbors

    def stats(self) -> Dict:
        return {"cache_size": len(self.cache), "max_cache": self.max_cache, **self.stats_data}

def run():
    mgr = MapTileManager(max_cache=10)
    x, y = mgr.latlon_to_tile(40.7128, -74.0060, 10)
    print(f"Tile: {x}, {y}")
    mgr.put_tile(Tile(x, y, 10, b"tile_data"))
    print(mgr.get_tile(x, y, 10))
    print(mgr.get_neighbors(x, y, 10))
    print(mgr.stats())

if __name__ == "__main__":
    run()
