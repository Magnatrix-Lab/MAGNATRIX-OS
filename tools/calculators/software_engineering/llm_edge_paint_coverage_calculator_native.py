"""Native stdlib module: Edge Paint Coverage Calculator
Calculates edge paint, primer, and topcoat needs for leather edges.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class EdgePaintCoverageCalculator:
    edge_length_mm: float
    edge_thickness_mm: float
    coats: int = 3
    paint_type: str = "waterbased"  # waterbased, acrylic, oil, wax

    _COVERAGE_MM_PER_ML = {
        "waterbased": 300, "acrylic": 250, "oil": 200, "wax": 400,
    }

    def edge_area_mm2(self) -> float:
        return self.edge_length_mm * self.edge_thickness_mm

    def paint_needed_ml(self) -> float:
        base = self._COVERAGE_MM_PER_ML.get(self.paint_type, 300)
        return (self.edge_area_mm2() / base) * self.coats

    def primer_needed_ml(self) -> float:
        return self.paint_needed_ml() * 0.3

    def topcoat_needed_ml(self) -> float:
        return self.paint_needed_ml() * 0.2

    def total_finish_ml(self) -> float:
        return self.paint_needed_ml() + self.primer_needed_ml() + self.topcoat_needed_ml()

    def drying_time_hours(self) -> float:
        times = {"waterbased": 0.5, "acrylic": 1, "oil": 4, "wax": 0.25}
        return times.get(self.paint_type, 1) * self.coats

    def cost(self, price_per_ml: float) -> float:
        return self.total_finish_ml() * price_per_ml

    def stats(self, price_per_ml: float = 0.1) -> Dict:
        return {
            "edge_length_mm": self.edge_length_mm,
            "edge_thickness_mm": self.edge_thickness_mm,
            "paint_type": self.paint_type,
            "coats": self.coats,
            "paint_needed_ml": round(self.paint_needed_ml(), 2),
            "primer_needed_ml": round(self.primer_needed_ml(), 2),
            "topcoat_needed_ml": round(self.topcoat_needed_ml(), 2),
            "total_finish_ml": round(self.total_finish_ml(), 2),
            "drying_time_hours": round(self.drying_time_hours(), 1),
            "cost_usd": round(self.cost(price_per_ml), 2),
        }

def run():
    epc = EdgePaintCoverageCalculator(edge_length_mm=200, edge_thickness_mm=2.5, coats=3, paint_type="acrylic")
    print(epc.stats())

if __name__ == "__main__":
    run()
