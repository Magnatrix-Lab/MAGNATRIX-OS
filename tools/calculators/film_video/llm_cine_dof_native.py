"""Native stdlib module: Cine DOF Calculator
Calculates depth of field, hyperfocal distance, and circle of confusion for cinema.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class CineDOFCalculator:
    focal_length_mm: float
    aperture_f: float
    subject_distance_m: float
    circle_of_confusion_mm: float = 0.029

    def hyperfocal_distance_m(self) -> float:
        if self.aperture_f == 0 or self.circle_of_confusion_mm == 0:
            return 0.0
        return (self.focal_length_mm ** 2) / (self.aperture_f * self.circle_of_confusion_mm) / 1000

    def near_limit_m(self) -> float:
        h = self.hyperfocal_distance_m()
        d = self.subject_distance_m
        if h == 0:
            return 0.0
        return (h * d) / (h + d)

    def far_limit_m(self) -> float:
        h = self.hyperfocal_distance_m()
        d = self.subject_distance_m
        if h <= d:
            return float('inf')
        return (h * d) / (h - d)

    def total_dof_m(self) -> float:
        far = self.far_limit_m()
        if far == float('inf'):
            return float('inf')
        return far - self.near_limit_m()

    def background_blur_mm(self, background_distance_m: float) -> float:
        if self.aperture_f == 0:
            return 0.0
        return (self.focal_length_mm * (background_distance_m - self.subject_distance_m)) / (self.aperture_f * background_distance_m)

    def stats(self) -> Dict:
        return {
            "focal_length_mm": self.focal_length_mm,
            "aperture_f": self.aperture_f,
            "subject_distance_m": self.subject_distance_m,
            "hyperfocal_m": round(self.hyperfocal_distance_m(), 2),
            "near_limit_m": round(self.near_limit_m(), 2),
            "far_limit_m": self.far_limit_m() if self.far_limit_m() != float('inf') else "inf",
            "total_dof_m": "inf" if self.total_dof_m() == float('inf') else round(self.total_dof_m(), 2),
        }

def run():
    cdof = CineDOFCalculator(focal_length_mm=50, aperture_f=2.8, subject_distance_m=3, circle_of_confusion_mm=0.029)
    print(cdof.stats())

if __name__ == "__main__":
    run()
