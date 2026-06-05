"""Native stdlib module: Ship Draft Calculator
Calculates vessel draft, displacement, and stability metrics for maritime operations.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class ShipDraftCalculator:
    vessel_name: str
    length_overall_m: float
    beam_m: float
    draft_design_m: float
    block_coefficient: float
    displacement_ton: float

    def waterplane_area_m2(self) -> float:
        return self.length_overall_m * self.beam_m * 0.85

    def displacement_volume_m3(self) -> float:
        return self.displacement_ton

    def block_volume_m3(self) -> float:
        return self.length_overall_m * self.beam_m * self.draft_design_m * self.block_coefficient

    def tons_per_cm_immersion(self) -> float:
        if self.waterplane_area_m2() == 0:
            return 0.0
        return self.waterplane_area_m2() / 100

    def draft_change_cm(self, added_weight_ton: float) -> float:
        tpc = self.tons_per_cm_immersion()
        if tpc == 0:
            return 0.0
        return added_weight_ton / tpc

    def metacentric_height_estimate_m(self) -> float:
        return self.beam_m / (2 * self.draft_design_m) if self.draft_design_m else 0

    def stats(self) -> Dict:
        return {
            "vessel": self.vessel_name,
            "draft_design_m": self.draft_design_m,
            "displacement_ton": self.displacement_ton,
            "waterplane_area_m2": round(self.waterplane_area_m2(), 1),
            "tons_per_cm": round(self.tons_per_cm_immersion(), 2),
            "gm_estimate_m": round(self.metacentric_height_estimate_m(), 2),
        }

def run():
    sdc = ShipDraftCalculator(vessel_name="MV Carrier", length_overall_m=200, beam_m=32, draft_design_m=12, block_coefficient=0.85, displacement_ton=50000)
    print(sdc.stats())

if __name__ == "__main__":
    run()
