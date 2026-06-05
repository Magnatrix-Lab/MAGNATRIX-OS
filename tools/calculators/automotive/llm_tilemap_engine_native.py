"""Tilemap Engine — layers, tilesets, collision, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum, auto

@dataclass
class Tile:
    tile_id: int
    solid: bool = False
    properties: Dict = field(default_factory=dict)

class TilemapLayer:
    def __init__(self, width: int, height: int, tile_size: int = 32):
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.data: List[List[int]] = [[0 for _ in range(width)] for _ in range(height)]
        self.tiles: Dict[int, Tile] = {0: Tile(0, False)}

    def set_tile(self, x: int, y: int, tile_id: int):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.data[y][x] = tile_id

    def get_tile(self, x: int, y: int) -> int:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.data[y][x]
        return 0

    def register_tile(self, tile: Tile):
        self.tiles[tile.tile_id] = tile

    def is_solid(self, x: int, y: int) -> bool:
        tile_id = self.get_tile(x, y)
        tile = self.tiles.get(tile_id)
        return tile.solid if tile else False

    def world_to_tile(self, wx: float, wy: float) -> Tuple[int, int]:
        return int(wx // self.tile_size), int(wy // self.tile_size)

class TilemapEngine:
    def __init__(self):
        self.layers: List[TilemapLayer] = []

    def add_layer(self, layer: TilemapLayer):
        self.layers.append(layer)

    def get_tile_at(self, wx: float, wy: float, layer_idx: int = 0) -> int:
        if layer_idx < len(self.layers):
            x, y = self.layers[layer_idx].world_to_tile(wx, wy)
            return self.layers[layer_idx].get_tile(x, y)
        return 0

    def is_solid_at(self, wx: float, wy: float, layer_idx: int = 0) -> bool:
        if layer_idx < len(self.layers):
            x, y = self.layers[layer_idx].world_to_tile(wx, wy)
            return self.layers[layer_idx].is_solid(x, y)
        return False

    def get_colliding_tiles(self, x: float, y: float, w: float, h: float) -> List[Tuple[int, int]]:
        tiles = []
        for layer in self.layers:
            tx1, ty1 = layer.world_to_tile(x, y)
            tx2, ty2 = layer.world_to_tile(x + w, y + h)
            for tx in range(tx1, tx2 + 1):
                for ty in range(ty1, ty2 + 1):
                    if layer.is_solid(tx, ty):
                        tiles.append((tx, ty))
        return tiles

    def stats(self) -> Dict:
        return {"layers": len(self.layers), "tiles": sum(sum(len(row) for row in l.data) for l in self.layers)}

def run():
    engine = TilemapEngine()
    layer = TilemapLayer(10, 10, 32)
    layer.register_tile(Tile(1, True, {"type": "wall"}))
    layer.set_tile(2, 2, 1)
    layer.set_tile(3, 2, 1)
    engine.add_layer(layer)
    print(engine.is_solid_at(70, 70))
    print(engine.get_colliding_tiles(60, 60, 40, 40))
    print(engine.stats())

if __name__ == "__main__":
    run()
