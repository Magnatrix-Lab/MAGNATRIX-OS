"""Native stdlib module: Cake Pan Sizing Calculator
Calculates pan volumes, batter scaling, and baking time adjustments.
"""
from dataclasses import dataclass
from typing import Dict, Optional
import math

@dataclass
class CakePanSizingCalculator:
    pan_diameter_cm: float
    pan_depth_cm: float
    pan_shape: str = "round"  # round, square, rectangular
    pan_length_cm: Optional[float] = None
    pan_width_cm: Optional[float] = None

    def pan_volume_ml(self) -> float:
        if self.pan_shape == "round":
            return math.pi * (self.pan_diameter_cm / 2) ** 2 * self.pan_depth_cm
        elif self.pan_shape == "square":
            return self.pan_diameter_cm ** 2 * self.pan_depth_cm
        elif self.pan_shape == "rectangular" and self.pan_length_cm and self.pan_width_cm:
            return self.pan_length_cm * self.pan_width_cm * self.pan_depth_cm
        return 0

    def batter_needed_ml(self, fill_pct: float = 70.0) -> float:
        return self.pan_volume_ml() * (fill_pct / 100)

    def scaling_factor_from_reference(self, reference_volume_ml: float) -> float:
        if reference_volume_ml == 0:
            return 0
        return self.pan_volume_ml() / reference_volume_ml

    def baking_time_adjustment_pct(self, reference_depth_cm: float = 5.0) -> float:
        if reference_depth_cm == 0:
            return 0
        return ((self.pan_depth_cm / reference_depth_cm) - 1) * 50

    def temperature_adjustment_c(self, reference_depth_cm: float = 5.0) -> float:
        if self.pan_depth_cm > reference_depth_cm * 1.5:
            return -10
        elif self.pan_depth_cm < reference_depth_cm * 0.7:
            return 5
        return 0

    def servings_estimate(self, serving_size_ml: float = 150) -> int:
        if serving_size_ml == 0:
            return 0
        return int(self.pan_volume_ml() / serving_size_ml)

    def stats(self, reference_volume_ml: Optional[float] = None, reference_depth_cm: float = 5.0) -> Dict:
        result = {
            "pan_shape": self.pan_shape,
            "pan_volume_ml": round(self.pan_volume_ml(), 1),
            "batter_needed_ml": round(self.batter_needed_ml(), 1),
            "baking_time_adjustment_pct": round(self.baking_time_adjustment_pct(reference_depth_cm), 1),
            "temperature_adjustment_c": self.temperature_adjustment_c(reference_depth_cm),
            "servings_estimate": self.servings_estimate(),
        }
        if reference_volume_ml is not None:
            result["scaling_factor"] = round(self.scaling_factor_from_reference(reference_volume_ml), 2)
        return result

def run():
    cpsc = CakePanSizingCalculator(pan_diameter_cm=20, pan_depth_cm=7, pan_shape="round")
    print(cpsc.stats(reference_volume_ml=1500, reference_depth_cm=5))

if __name__ == "__main__":
    run()
