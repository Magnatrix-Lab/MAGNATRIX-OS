"""
Metabolic Syndrome Calculator — Endocrinology
ATP III/NCEP criteria for metabolic syndrome diagnosis.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class MetabolicProfile:
    waist_cm: float
    triglycerides_mg_dl: float
    hdl_mg_dl: float
    systolic_bp: float
    diastolic_bp: float
    fasting_glucose_mg_dl: float
    gender: str  # "male" or "female"
    on_bp_medication: bool = False
    on_lipid_medication: bool = False
    on_diabetes_medication: bool = False
    ethnicity: str = "caucasian"  # asian has lower waist threshold


@dataclass
class MetabolicResult:
    criteria_met: int
    total_criteria: int
    metabolic_syndrome: bool
    criteria_details: dict
    ten_year_cv_risk: str
    recommendations: List[str]
    follow_up: str


class MetabolicSyndromeCalculator:
    """Metabolic syndrome diagnosis per ATP III/NCEP criteria."""

    def calculate(self, profile: MetabolicProfile) -> MetabolicResult:
        criteria = {}

        # Waist circumference (ethnicity adjusted)
        if profile.ethnicity.lower() in ["asian", "south_asian", "chinese", "japanese"]:
            waist_threshold = 80 if profile.gender.lower() == "female" else 90
        else:
            waist_threshold = 88 if profile.gender.lower() == "female" else 102

        criteria["waist"] = profile.waist_cm > waist_threshold

        # Triglycerides
        criteria["triglycerides"] = profile.triglycerides_mg_dl >= 150 or profile.on_lipid_medication

        # HDL
        hdl_threshold = 50 if profile.gender.lower() == "female" else 40
        criteria["hdl"] = profile.hdl_mg_dl < hdl_threshold or profile.on_lipid_medication

        # BP
        criteria["blood_pressure"] = profile.systolic_bp >= 130 or profile.diastolic_bp >= 85 or profile.on_bp_medication

        # Glucose
        criteria["glucose"] = profile.fasting_glucose_mg_dl >= 100 or profile.on_diabetes_medication

        met = sum(criteria.values())
        syndrome = met >= 3

        # CV risk estimate (very rough)
        if met >= 4:
            cv_risk = "High 10-year cardiovascular risk"
        elif met == 3:
            cv_risk = "Moderate-to-high CV risk"
        elif met == 2:
            cv_risk = "Moderate CV risk"
        else:
            cv_risk = "Low-to-moderate CV risk"

        recs = ["Weight reduction (target 7-10% loss)", "150 min/week moderate exercise", "Mediterranean diet"]
        if criteria["triglycerides"] or criteria["hdl"]:
            recs.append("Address dyslipidemia — statin if LDL elevated or high risk")
        if criteria["blood_pressure"]:
            recs.append("BP control target <130/80")
        if criteria["glucose"]:
            recs.append("Glucose management — metformin if prediabetes")
        if criteria["waist"]:
            recs.append("Central obesity reduction — calorie restriction + exercise")

        return MetabolicResult(
            criteria_met=met,
            total_criteria=5,
            metabolic_syndrome=syndrome,
            criteria_details={k: "Met" if v else "Not met" for k, v in criteria.items()},
            ten_year_cv_risk=cv_risk,
            recommendations=recs,
            follow_up="Recheck lipids, glucose, BP every 3-6 months"
        )


def run():
    calc = MetabolicSyndromeCalculator()

    print("=" * 60)
    print("Metabolic Syndrome Calculator")
    print("=" * 60)

    profile = MetabolicProfile(
        waist_cm=105, triglycerides_mg_dl=180, hdl_mg_dl=38,
        systolic_bp=138, diastolic_bp=88, fasting_glucose_mg_dl=108,
        gender="male", ethnicity="caucasian"
    )

    result = calc.calculate(profile)
    print(f"\nCriteria met: {result.criteria_met}/{result.total_criteria}")
    print(f"Metabolic syndrome: {result.metabolic_syndrome}")
    print(f"Details: {result.criteria_details}")
    print(f"CV Risk: {result.ten_year_cv_risk}")
    print(f"Recommendations: {result.recommendations}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
