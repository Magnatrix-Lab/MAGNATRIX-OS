"""Native stdlib module: Stratigraphy Calculator
Calculates layer depths, dating ranges, and sedimentation rates for archaeological sites.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class StratigraphicLayer:
    layer_id: str
    top_depth_cm: float
    bottom_depth_cm: float
    estimated_age_bp: float
    material: str

@dataclass
class StratigraphyCalculator:
    site_name: str
    layers: List[StratigraphicLayer] = field(default_factory=list)

    def total_depth_cm(self) -> float:
        if not self.layers:
            return 0.0
        return max(l.bottom_depth_cm for l in self.layers)

    def sedimentation_rate_cm_per_100yr(self, layer: StratigraphicLayer) -> float:
        thickness = layer.bottom_depth_cm - layer.top_depth_cm
        if layer.estimated_age_bp <= 0:
            return 0.0
        return (thickness / layer.estimated_age_bp) * 100

    def avg_sedimentation_rate(self) -> float:
        if not self.layers:
            return 0.0
        rates = [self.sedimentation_rate_cm_per_100yr(l) for l in self.layers]
        return sum(rates) / len(rates)

    def layer_thicknesses(self) -> Dict[str, float]:
        return {l.layer_id: round(l.bottom_depth_cm - l.top_depth_cm, 1) for l in self.layers}

    def age_range(self) -> tuple:
        ages = [l.estimated_age_bp for l in self.layers]
        return (max(ages), min(ages)) if ages else (0, 0)

    def stats(self) -> Dict:
        return {
            "site": self.site_name,
            "layers": len(self.layers),
            "total_depth_cm": round(self.total_depth_cm(), 1),
            "avg_sedimentation_rate": round(self.avg_sedimentation_rate(), 3),
            "thicknesses": self.layer_thicknesses(),
            "age_range": self.age_range(),
        }

def run():
    sc = StratigraphyCalculator(
        site_name="Cave A",
        layers=[
            StratigraphicLayer("L1", 0, 15, 500, "ash"),
            StratigraphicLayer("L2", 15, 45, 2000, "clay"),
            StratigraphicLayer("L3", 45, 80, 5000, "sand"),
            StratigraphicLayer("L4", 80, 120, 10000, "gravel"),
        ]
    )
    print(sc.stats())

if __name__ == "__main__":
    run()
