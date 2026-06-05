"""Native stdlib module: Tile Calculator
Calculates tile quantities, grout, and adhesive for tiling projects.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class TileCalculator:
    area_name: str
    area_width_m: float
    area_height_m: float
    tile_width_m: float
    tile_height_m: float
    tile_spacing_mm: float = 3.0
    wastage_pct: float = 10.0
    cost_per_m2: float = 25.0

    def area_m2(self) -> float:
        return self.area_width_m * self.area_height_m

    def tiles_per_row(self) -> int:
        if self.tile_width_m == 0:
            return 0
        spacing_m = self.tile_spacing_mm / 1000
        return int(self.area_width_m / (self.tile_width_m + spacing_m)) + 1

    def tiles_per_column(self) -> int:
        if self.tile_height_m == 0:
            return 0
        spacing_m = self.tile_spacing_mm / 1000
        return int(self.area_height_m / (self.tile_height_m + spacing_m)) + 1

    def total_tiles(self) -> int:
        return int(self.tiles_per_row() * self.tiles_per_column() * (1 + self.wastage_pct / 100))

    def grout_kg(self) -> float:
        return self.area_m2() * 0.5

    def adhesive_kg(self) -> float:
        return self.area_m2() * 3.5

    def total_cost(self) -> float:
        return self.area_m2() * self.cost_per_m2

    def stats(self) -> Dict:
        return {
            "area": self.area_name,
            "area_m2": round(self.area_m2(), 2),
            "tiles_per_row": self.tiles_per_row(),
            "tiles_per_column": self.tiles_per_column(),
            "total_tiles": self.total_tiles(),
            "grout_kg": round(self.grout_kg(), 1),
            "adhesive_kg": round(self.adhesive_kg(), 1),
            "total_cost": round(self.total_cost(), 2),
        }

def run():
    tc = TileCalculator(area_name="Bathroom Wall", area_width_m=2.5, area_height_m=2.0, tile_width_m=0.3, tile_height_m=0.6, cost_per_m2=40)
    print(tc.stats())

if __name__ == "__main__":
    run()
