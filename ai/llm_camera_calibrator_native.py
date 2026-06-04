"""Camera Calibrator - Intrinsic parameters for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math

@dataclass
class CameraCalibrator:
    focal_length: float = 1.0
    cx: float = 0.0
    cy: float = 0.0

    def project(self, point_3d: Tuple[float, float, float]) -> Tuple[float, float]:
        x, y, z = point_3d
        if z <= 0: return (0.0, 0.0)
        u = self.focal_length * x / z + self.cx
        v = self.focal_length * y / z + self.cy
        return (u, v)

    def unproject(self, point_2d: Tuple[float, float], depth: float) -> Tuple[float, float, float]:
        u, v = point_2d
        x = (u - self.cx) * depth / self.focal_length
        y = (v - self.cy) * depth / self.focal_length
        return (x, y, depth)

    def stats(self) -> dict:
        return {"focal": self.focal_length, "cx": self.cx, "cy": self.cy}

def run():
    cc = CameraCalibrator(2.0, 320, 240)
    print("Project (1,1,2):", cc.project((1, 1, 2)))
    print("Unproject (321, 241, 2):", cc.unproject((321, 241), 2))
    print("Stats:", cc.stats())

if __name__ == "__main__": run()
