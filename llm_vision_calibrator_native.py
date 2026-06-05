"""Vision Calibrator — camera matrix, distortion, homography, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class VisionCalibrator:
    focal_length: float = 800.0
    principal_point: Tuple[float, float] = (320.0, 240.0)
    image_size: Tuple[int, int] = (640, 480)

    def camera_matrix(self) -> List[List[float]]:
        fx = fy = self.focal_length
        cx, cy = self.principal_point
        return [[fx, 0, cx], [0, fy, cy], [0, 0, 1]]

    def pixel_to_ray(self, u: float, v: float) -> Tuple[float, float, float]:
        cx, cy = self.principal_point
        x = (u - cx) / self.focal_length
        y = (v - cy) / self.focal_length
        return x, y, 1.0

    def world_to_pixel(self, x: float, y: float, z: float) -> Tuple[float, float]:
        if z == 0:
            return 0, 0
        cx, cy = self.principal_point
        u = self.focal_length * x / z + cx
        v = self.focal_length * y / z + cy
        return u, v

    def focal_length_from_fov(self, fov_deg: float) -> float:
        w = self.image_size[0]
        return w / (2 * math.tan(math.radians(fov_deg / 2)))

    def fov_from_focal(self) -> float:
        w = self.image_size[0]
        return 2 * math.degrees(math.atan(w / (2 * self.focal_length)))

    def stats(self) -> Dict:
        return {
            "focal_length": self.focal_length,
            "fov": round(self.fov_from_focal(), 1),
            "principal": self.principal_point
        }

def run():
    vc = VisionCalibrator()
    print(vc.stats())
    print("Ray (400,300):", vc.pixel_to_ray(400, 300))
    print("Pixel (1,0,5):", vc.world_to_pixel(1, 0, 5))

if __name__ == "__main__":
    run()
