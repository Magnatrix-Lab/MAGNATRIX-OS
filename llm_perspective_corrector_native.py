"""Perspective Corrector — homography, vanishing point, keystone, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class PerspectiveCorrector:
    def line_intersection(self, p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float], p4: Tuple[float, float]) -> Optional[Tuple[float, float]]:
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-10:
            return None
        px = ((x1*y2 - y1*x2)*(x3 - x4) - (x1 - x2)*(x3*y4 - y3*x4)) / denom
        py = ((x1*y2 - y1*x2)*(y3 - y4) - (y1 - y2)*(x3*y4 - y3*x4)) / denom
        return px, py

    def vanishing_point(self, lines: List[Tuple[Tuple[float, float], Tuple[float, float]]]) -> Optional[Tuple[float, float]]:
        if len(lines) < 2:
            return None
        intersections = []
        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                inter = self.line_intersection(lines[i][0], lines[i][1], lines[j][0], lines[j][1])
                if inter:
                    intersections.append(inter)
        if not intersections:
            return None
        return sum(x for x, y in intersections) / len(intersections), sum(y for x, y in intersections) / len(intersections)

    def keystone_correction(self, src: List[Tuple[float, float]], dst: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        if len(src) != 4 or len(dst) != 4:
            return src
        return dst

    def aspect_ratio(self, width_px: float, height_px: float, sensor_width: float = 36.0, sensor_height: float = 24.0) -> float:
        return (width_px / sensor_width) / (height_px / sensor_height)

    def stats(self, lines: List[Tuple[Tuple[float, float], Tuple[float, float]]]) -> Dict:
        vp = self.vanishing_point(lines)
        return {"vanishing_point": vp, "lines": len(lines)}

def run():
    pc = PerspectiveCorrector()
    lines = [((0,0),(100,50)), ((0,100),(100,75))]
    print(pc.stats(lines))

if __name__ == "__main__":
    run()
