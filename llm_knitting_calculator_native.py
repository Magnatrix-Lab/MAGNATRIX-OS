"""Native stdlib module: Knitting Calculator
Calculates stitch counts, gauge, and yarn requirements for knitting projects.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class YarnWeight(Enum):
    LACE = "lace"
    FINGERING = "fingering"
    SPORT = "sport"
    DK = "dk"
    WORSTED = "worsted"
    BULKY = "bulky"
    SUPER_BULKY = "super_bulky"

@dataclass
class KnittingCalculator:
    project_name: str
    width_cm: float
    length_cm: float
    gauge_stitches_per_10cm: float
    gauge_rows_per_10cm: float
    yarn_weight: YarnWeight
    yarn_meters_per_100g: float = 200

    def total_stitches(self) -> int:
        stitches_per_cm = self.gauge_stitches_per_10cm / 10
        return int(self.width_cm * stitches_per_cm)

    def total_rows(self) -> int:
        rows_per_cm = self.gauge_rows_per_10cm / 10
        return int(self.length_cm * rows_per_cm)

    def total_stitch_count(self) -> int:
        return self.total_stitches() * self.total_rows()

    def yarn_length_m(self) -> float:
        if self.gauge_stitches_per_10cm == 0:
            return 0.0
        stitches_per_m = self.gauge_stitches_per_10cm * 10
        return (self.total_stitch_count() / stitches_per_m) * 1.5

    def yarn_weight_g(self) -> float:
        if self.yarn_meters_per_100g == 0:
            return 0.0
        return (self.yarn_length_m() / self.yarn_meters_per_100g) * 100

    def yarn_skeins(self, skein_weight_g: float = 100) -> int:
        if skein_weight_g == 0:
            return 0
        return int(self.yarn_weight_g() / skein_weight_g) + (1 if self.yarn_weight_g() % skein_weight_g > 0 else 0)

    def stats(self) -> Dict:
        return {
            "project": self.project_name,
            "total_stitches": self.total_stitches(),
            "total_rows": self.total_rows(),
            "total_stitch_count": self.total_stitch_count(),
            "yarn_length_m": round(self.yarn_length_m(), 1),
            "yarn_weight_g": round(self.yarn_weight_g(), 1),
            "skeins_needed": self.yarn_skeins(),
        }

def run():
    kc = KnittingCalculator(
        project_name="Scarf",
        width_cm=25,
        length_cm=180,
        gauge_stitches_per_10cm=20,
        gauge_rows_per_10cm=28,
        yarn_weight=YarnWeight.WORSTED,
        yarn_meters_per_100g=180
    )
    print(kc.stats())

if __name__ == "__main__":
    run()
