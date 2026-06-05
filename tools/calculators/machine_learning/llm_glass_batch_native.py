"""Native stdlib module: Glass Batch Calculator
Calculates glass batch compositions, melting points, and thermal properties.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class BatchComponent:
    name: str
    weight_kg: float
    sio2_pct: float
    na2o_pct: float
    cao_pct: float
    al2o3_pct: float

@dataclass
class GlassBatchCalculator:
    batch_name: str
    target_weight_kg: float
    components: List[BatchComponent] = field(default_factory=list)

    def total_weight_kg(self) -> float:
        return sum(c.weight_kg for c in self.components)

    def composition_pct(self, oxide_pct_attr: str) -> float:
        if self.total_weight_kg() == 0:
            return 0.0
        total_oxide = sum(getattr(c, oxide_pct_attr) * c.weight_kg for c in self.components)
        return (total_oxide / self.total_weight_kg())

    def sio2_pct(self) -> float:
        return self.composition_pct("sio2_pct")

    def na2o_pct(self) -> float:
        return self.composition_pct("na2o_pct")

    def cao_pct(self) -> float:
        return self.composition_pct("cao_pct")

    def al2o3_pct(self) -> float:
        return self.composition_pct("al2o3_pct")

    def estimated_melting_point_c(self) -> float:
        sio2 = self.sio2_pct()
        na2o = self.na2o_pct()
        cao = self.cao_pct()
        base = 1700
        return base - 10 * na2o - 5 * cao - 2 * (100 - sio2 - na2o - cao)

    def thermal_expansion_estimate(self) -> float:
        na2o = self.na2o_pct()
        return 5 + 0.2 * na2o

    def cullet_pct(self) -> float:
        if self.total_weight_kg() == 0:
            return 0.0
        cullet_weight = sum(c.weight_kg for c in self.components if "cullet" in c.name.lower())
        return (cullet_weight / self.total_weight_kg()) * 100

    def stats(self) -> Dict:
        return {
            "batch": self.batch_name,
            "total_weight_kg": round(self.total_weight_kg(), 1),
            "sio2_pct": round(self.sio2_pct(), 2),
            "na2o_pct": round(self.na2o_pct(), 2),
            "cao_pct": round(self.cao_pct(), 2),
            "al2o3_pct": round(self.al2o3_pct(), 2),
            "melting_point_c": round(self.estimated_melting_point_c(), 1),
            "thermal_expansion": round(self.thermal_expansion_estimate(), 2),
            "cullet_pct": round(self.cullet_pct(), 1),
        }

def run():
    gbc = GlassBatchCalculator(
        batch_name="Soda-Lime Glass",
        target_weight_kg=1000,
        components=[
            BatchComponent("silica_sand", 600, 99, 0, 0, 0),
            BatchComponent("soda_ash", 200, 0, 58, 0, 0),
            BatchComponent("limestone", 150, 2, 0, 55, 0),
            BatchComponent("alumina", 30, 0, 0, 0, 99),
            BatchComponent("cullet", 100, 72, 14, 10, 2),
        ]
    )
    print(gbc.stats())

if __name__ == "__main__":
    run()
