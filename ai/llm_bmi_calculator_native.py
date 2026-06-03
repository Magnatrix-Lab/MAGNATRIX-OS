"""LLM BMI Calculator — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class BMIStatus(Enum):
    UNDERWEIGHT = auto()
    NORMAL = auto()
    OVERWEIGHT = auto()
    OBESE = auto()
    SEVERELY_OBESE = auto()

class BMICalculator:
    def __init__(self) -> None:
        pass

    def calculate(self, weight_kg: float, height_m: float) -> float:
        if height_m <= 0:
            return 0.0
        return weight_kg / (height_m * height_m)

    def calculate_imperial(self, weight_lb: float, height_in: float) -> float:
        if height_in <= 0:
            return 0.0
        return 703 * weight_lb / (height_in * height_in)

    def get_status(self, bmi: float) -> BMIStatus:
        if bmi < 18.5:
            return BMIStatus.UNDERWEIGHT
        elif bmi < 25:
            return BMIStatus.NORMAL
        elif bmi < 30:
            return BMIStatus.OVERWEIGHT
        elif bmi < 35:
            return BMIStatus.OBESE
        return BMIStatus.SEVERELY_OBESE

    def get_ideal_weight(self, height_m: float) -> Tuple[float, float]:
        min_w = 18.5 * height_m * height_m
        max_w = 24.9 * height_m * height_m
        return (min_w, max_w)

    def get_stats(self, weight_kg: float, height_m: float) -> Dict[str, Any]:
        bmi = self.calculate(weight_kg, height_m)
        status = self.get_status(bmi)
        ideal = self.get_ideal_weight(height_m)
        return {"bmi": round(bmi, 2), "status": status.name, "ideal_weight": str(round(ideal[0], 1)) + "-" + str(round(ideal[1], 1)) + " kg"}

def run() -> None:
    print("BMI Calculator test")
    e = BMICalculator()
    print("  70kg, 1.75m: " + str(e.get_stats(70, 1.75)))
    print("  50kg, 1.70m: " + str(e.get_stats(50, 1.70)))
    print("  90kg, 1.70m: " + str(e.get_stats(90, 1.70)))
    print("  150lb, 70in: " + str(e.calculate_imperial(150, 70)))
    print("BMI Calculator test complete.")

if __name__ == "__main__":
    run()
