"""
eGFR Calculator — Nephrology
CKD-EPI 2021 race-free equation and creatinine-based estimation.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum
import math


class Gender(Enum):
    MALE = "male"
    FEMALE = "female"


class CKDStage(Enum):
    G1 = "G1"   # Normal or high, >=90
    G2 = "G2"   # Mildly decreased, 60-89
    G3A = "G3a" # Mildly to moderately decreased, 45-59
    G3B = "G3b" # Moderately to severely decreased, 30-44
    G4 = "G4"   # Severely decreased, 15-29
    G5 = "G5"   # Kidney failure, <15


@dataclass
class eGFRProfile:
    creatinine_mg_dl: float
    age: int
    gender: Gender
    cystatin_c_mg_l: float = 0.0


@dataclass
class eGFRResult:
    egfr_creatinine: float
    egfr_cystatin_c: float
    egfr_combined: float
    ckd_stage: CKDStage
    stage_description: str
    annual_decline_risk: str
    recommendations: List[str]
    follow_up: str


class eGFRCalculator:
    """CKD-EPI 2021 race-free eGFR calculator."""

    def calculate(self, profile: eGFRProfile) -> eGFRResult:
        cr = profile.creatinine_mg_dl
        age = profile.age
        is_female = profile.gender == Gender.FEMALE

        # CKD-EPI 2021 (race-free)
        kappa = 0.7 if is_female else 0.9
        alpha = -0.241 if is_female else -0.302
        beta = 1.0 if is_female else 1.0
        female_factor = 0.9938 if is_female else 1.0

        min_cr_k = min(cr / kappa, 1.0)
        max_cr_k = max(cr / kappa, 1.0)

        egfr_cr = 142 * (min_cr_k ** alpha) * (max_cr_k ** -1.200) * (0.9938 ** age) * beta

        # Cystatin C eGFR if available
        egfr_cys = 0.0
        egfr_combined = 0.0
        if profile.cystatin_c_mg_l > 0:
            cys = profile.cystatin_c_mg_l
            min_cys = min(cys / 0.8, 1.0)
            max_cys = max(cys / 0.8, 1.0)
            cys_alpha = -0.219 if is_female else -0.219  # same for both in 2021
            egfr_cys = 133 * (min_cys ** cys_alpha) * (max_cys ** -0.544) * (0.9961 ** age) * (0.979 if is_female else 1.0)
            # Combined (not fully implemented here — simplified)
            egfr_combined = (egfr_cr + egfr_cys) / 2
        else:
            egfr_cys = 0.0
            egfr_combined = egfr_cr

        # Stage
        if egfr_cr >= 90:
            stage = CKDStage.G1
            desc = "Normal or high GFR"
        elif egfr_cr >= 60:
            stage = CKDStage.G2
            desc = "Mildly decreased GFR"
        elif egfr_cr >= 45:
            stage = CKDStage.G3A
            desc = "Mildly to moderately decreased GFR"
        elif egfr_cr >= 30:
            stage = CKDStage.G3B
            desc = "Moderately to severely decreased GFR"
        elif egfr_cr >= 15:
            stage = CKDStage.G4
            desc = "Severely decreased GFR"
        else:
            stage = CKDStage.G5
            desc = "Kidney failure"

        # Decline risk
        if stage in [CKDStage.G4, CKDStage.G5]:
            decline = "High risk of ESRD — nephrology referral essential"
        elif stage == CKDStage.G3B:
            decline = "Moderate risk — monitor for progression"
        elif stage in [CKDStage.G3A, CKDStage.G2]:
            decline = "Low-to-moderate risk — annual monitoring"
        else:
            decline = "Low risk if no albuminuria"

        recs = ["BP control <130/80", "Avoid nephrotoxic drugs (NSAIDs, contrast)"]
        if stage.value in ["G3a", "G3b", "G4", "G5"]:
            recs += ["Nephrology referral", "ACEi/ARB if albuminuria", "Sodium restriction <2g/day"]
        if stage == CKDStage.G5:
            recs += ["Dialysis education", "Transplant evaluation", "Vascular access planning"]
        if stage.value in ["G3a", "G3b", "G4", "G5"]:
            recs += ["Anemia workup (EPO if indicated)", "BMP, phosphate, PTH, vitamin D monitoring"]

        follow = "Annual eGFR" if stage in [CKDStage.G1, CKDStage.G2] else "Every 3-6 months"
        if stage == CKDStage.G5:
            follow = "Monthly (or per dialysis schedule)"

        return eGFRResult(
            egfr_creatinine=round(egfr_cr, 1),
            egfr_cystatin_c=round(egfr_cys, 1) if egfr_cys > 0 else 0.0,
            egfr_combined=round(egfr_combined, 1),
            ckd_stage=stage,
            stage_description=desc,
            annual_decline_risk=decline,
            recommendations=recs,
            follow_up=follow
        )

    def creatinine_clearance_cockcroft_gault(self, creatinine_mg_dl: float, weight_kg: float, age: int, gender: str) -> float:
        """Cockcroft-Gault for drug dosing."""
        cg = ((140 - age) * weight_kg) / (72 * creatinine_mg_dl)
        if gender.lower() == "female":
            cg *= 0.85
        return round(cg, 1)


def run():
    calc = eGFRCalculator()

    print("=" * 60)
    print("eGFR Calculator")
    print("=" * 60)

    profile = eGFRProfile(creatinine_mg_dl=2.1, age=68, gender=Gender.MALE, cystatin_c_mg_l=1.5)
    result = calc.calculate(profile)
    print(f"\neGFR (Cr): {result.egfr_creatinine}")
    print(f"eGFR (CysC): {result.egfr_cystatin_c}")
    print(f"Combined: {result.egfr_combined}")
    print(f"Stage: {result.ckd_stage.value} — {result.stage_description}")
    print(f"Decline risk: {result.annual_decline_risk}")
    print(f"Recommendations: {result.recommendations}")
    print(f"Follow-up: {result.follow_up}")

    print(f"\nCockcroft-Gault (70kg, 68M, Cr 2.1): {calc.creatinine_clearance_cockcroft_gault(2.1, 70, 68, 'male')} mL/min")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
