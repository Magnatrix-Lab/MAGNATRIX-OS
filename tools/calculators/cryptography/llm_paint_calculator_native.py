"""Native stdlib module: Paint Calculator
Calculates paint quantity, coverage, and cost for interior and exterior surfaces.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Surface:
    name: str
    width_m: float
    height_m: float
    coats: int = 1
    non_paintable_m2: float = 0.0

@dataclass
class PaintCalculator:
    project_name: str
    surfaces: List[Surface] = field(default_factory=list)
    coverage_m2_per_l: float = 10.0
    paint_cost_per_l: float = 25.0

    def paintable_area_m2(self, surface: Surface) -> float:
        return max(0, (surface.width_m * surface.height_m) - surface.non_paintable_m2)

    def total_area_m2(self) -> float:
        return sum(self.paintable_area_m2(s) for s in self.surfaces)

    def total_coated_area_m2(self) -> float:
        return sum(self.paintable_area_m2(s) * s.coats for s in self.surfaces)

    def paint_needed_l(self) -> float:
        if self.coverage_m2_per_l == 0:
            return 0.0
        return self.total_coated_area_m2() / self.coverage_m2_per_l

    def paint_needed_cans(self, can_size_l: float = 4) -> int:
        if can_size_l == 0:
            return 0
        return int(self.paint_needed_l() / can_size_l) + (1 if self.paint_needed_l() % can_size_l > 0 else 0)

    def total_cost(self) -> float:
        return self.paint_needed_l() * self.paint_cost_per_l

    def stats(self, can_size_l: float = 4) -> Dict:
        return {
            "project": self.project_name,
            "surfaces": len(self.surfaces),
            "total_area_m2": round(self.total_area_m2(), 1),
            "coated_area_m2": round(self.total_coated_area_m2(), 1),
            "paint_needed_l": round(self.paint_needed_l(), 1),
            "cans_needed": self.paint_needed_cans(can_size_l),
            "total_cost": round(self.total_cost(), 2),
        }

def run():
    pc = PaintCalculator(
        project_name="Living Room",
        coverage_m2_per_l=12,
        paint_cost_per_l=30,
        surfaces=[
            Surface("wall_1", 4.5, 2.8, 2, 4.0),
            Surface("wall_2", 3.5, 2.8, 2, 2.5),
            Surface("wall_3", 4.5, 2.8, 2, 3.0),
            Surface("wall_4", 3.5, 2.8, 2, 2.0),
        ]
    )
    print(pc.stats())

if __name__ == "__main__":
    run()
