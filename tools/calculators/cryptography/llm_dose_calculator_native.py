"""Dose Calculator — mg/kg, BSA, renal adjustment, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class DoseCalculator:
    weight_kg: float = 70.0
    height_cm: float = 170.0
    age: int = 30
    creatinine_clearance: float = 90.0

    def bsa_m2(self) -> float:
        return math.sqrt(self.weight_kg * self.height_cm / 3600)

    def mg_per_kg(self, dose_mg_kg: float) -> float:
        return dose_mg_kg * self.weight_kg

    def bsa_dose(self, dose_per_m2: float) -> float:
        return dose_per_m2 * self.bsa_m2()

    def renal_adjustment(self, normal_dose: float, threshold_crcl: float = 50.0) -> float:
        if self.creatinine_clearance >= threshold_crcl:
            return normal_dose
        return normal_dose * max(0.25, self.creatinine_clearance / threshold_crcl)

    def pediatric_dose(self, adult_dose: float, age_months: int = None) -> float:
        age_m = age_months or self.age * 12
        if age_m < 12:
            return adult_dose * (age_m / 150)
        elif age_m < 108:
            return adult_dose * (age_m / 168)
        return adult_dose

    def max_safe_dose(self, max_mg_kg: float) -> float:
        return max_mg_kg * self.weight_kg

    def stats(self, dose_mg_kg: float = 5.0) -> Dict:
        return {
            "bsa": round(self.bsa_m2(), 2),
            "mg_kg_dose": round(self.mg_per_kg(dose_mg_kg), 1),
            "bsa_dose": round(self.bsa_dose(100), 1)
        }

def run():
    dc = DoseCalculator(weight_kg=80, height_cm=180, creatinine_clearance=35)
    print(dc.stats())
    print("Renal adjusted:", dc.renal_adjustment(500))
    print("Pediatric:", dc.pediatric_dose(500, 36))

if __name__ == "__main__":
    run()
