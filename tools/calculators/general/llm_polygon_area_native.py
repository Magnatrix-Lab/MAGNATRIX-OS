"""Native stdlib module: Polygon Area Calculator
Calculates polygon area and centroid from coordinate vertices.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import math

@dataclass
class PolygonAreaCalculator:
    polygon_name: str
    vertices: List[Tuple[float, float]] = field(default_factory=list)

    def area_sq_m(self) -> float:
        if len(self.vertices) < 3:
            return 0.0
        n = len(self.vertices)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            lat1, lon1 = math.radians(self.vertices[i][0]), math.radians(self.vertices[i][1])
            lat2, lon2 = math.radians(self.vertices[j][0]), math.radians(self.vertices[j][1])
            area += (lon2 - lon1) * (2 + math.sin(lat1) + math.sin(lat2))
        area = abs(area) * 6371000 * 6371000 / 2.0
        return area

    def area_hectares(self) -> float:
        return self.area_sq_m() / 10000

    def area_sq_km(self) -> float:
        return self.area_sq_m() / 1_000_000

    def centroid(self) -> Tuple[float, float]:
        if len(self.vertices) < 3:
            return (0.0, 0.0)
        n = len(self.vertices)
        cx = sum(v[0] for v in self.vertices) / n
        cy = sum(v[1] for v in self.vertices) / n
        return (round(cx, 6), round(cy, 6))

    def perimeter_m(self) -> float:
        if len(self.vertices) < 2:
            return 0.0
        total = 0.0
        for i in range(len(self.vertices)):
            j = (i + 1) % len(self.vertices)
            lat1, lon1 = math.radians(self.vertices[i][0]), math.radians(self.vertices[i][1])
            lat2, lon2 = math.radians(self.vertices[j][0]), math.radians(self.vertices[j][1])
            dlon = lon2 - lon1
            a = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
            total += 6371000 * 2 * math.asin(math.sqrt(a))
        return total

    def stats(self) -> Dict:
        return {
            "polygon": self.polygon_name,
            "vertices": len(self.vertices),
            "area_sq_m": round(self.area_sq_m(), 1),
            "area_hectares": round(self.area_hectares(), 3),
            "area_sq_km": round(self.area_sq_km(), 6),
            "perimeter_m": round(self.perimeter_m(), 1),
            "centroid": self.centroid(),
        }

def run():
    pac = PolygonAreaCalculator(
        polygon_name="Farm Field",
        vertices=[
            (40.0, -75.0),
            (40.0, -74.9),
            (39.9, -74.9),
            (39.9, -75.0),
        ]
    )
    print(pac.stats())

if __name__ == "__main__":
    run()
