"""Camera Optimizer — depth of field, hyperfocal, exposure, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class CameraOptimizer:
    focal_length_mm: float = 50.0
    aperture: float = 2.8
    sensor_width_mm: float = 36.0

    def hyperfocal(self, circle_of_confusion_mm: float = 0.03) -> float:
        return (self.focal_length_mm ** 2) / (self.aperture * circle_of_confusion_mm) + self.focal_length_mm if self.aperture > 0 else 0.0

    def dof_near(self, focus_distance_m: float = 5.0) -> float:
        h = self.hyperfocal()
        d = focus_distance_m * 1000.0
        return (h * d) / (h + d) / 1000.0 if (h + d) > 0 else 0.0

    def dof_far(self, focus_distance_m: float = 5.0) -> float:
        h = self.hyperfocal()
        d = focus_distance_m * 1000.0
        return (h * d) / (h - d) / 1000.0 if (h - d) > 0 else float("inf")

    def fov_horizontal(self) -> float:
        return 2 * math.atan(self.sensor_width_mm / (2 * self.focal_length_mm)) * (180 / math.pi) if self.focal_length_mm > 0 else 0.0

    def stats(self) -> Dict:
        return {"hyperfocal_m": round(self.hyperfocal() / 1000.0, 2), "dof_near_m": round(self.dof_near(), 2), "fov_deg": round(self.fov_horizontal(), 2)}

def run():
    co = CameraOptimizer(focal_length_mm=35, aperture=1.8)
    print(co.stats())

if __name__ == "__main__":
    run()
