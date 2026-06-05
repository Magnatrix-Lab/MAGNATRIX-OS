"""
Osteoporosis Risk Calculator — Endocrinology
FRAX-inspired 10-year fracture risk estimation.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class RiskLevel(Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


@dataclass
class OsteoporosisProfile:
    age: int
    gender: str
    weight_kg: float
    height_cm: float
    family_history_hip_fracture: bool = False
    previous_fracture: bool = False
    smoker: bool = False
    alcohol_3_plus_units_daily: bool = False
    rheumatoid_arthritis: bool = False
    secondary_osteoporosis: bool = False  # e.g., glucocorticoids, hyperthyroidism
    femoral_neck_bmd_t_score: float = 0.0


@dataclass
class OsteoporosisResult:
    major_fracture_10yr_percent: float
    hip_fracture_10yr_percent: float
    risk_level: RiskLevel
    t_score_interpretation: str
    bmd_category: str
    treatment_recommended: bool
    recommendations: List[str]
    follow_up: str


class OsteoporosisCalculator:
    """Simplified FRAX-style fracture risk estimation."""

    def calculate(self, profile: OsteoporosisProfile) -> OsteoporosisResult:
        # Base risk by age and gender (simplified approximation)
        if profile.gender.lower() == "female":
            base_major = 0.5 + profile.age * 0.15
            base_hip = 0.2 + profile.age * 0.08
        else:
            base_major = 0.3 + profile.age * 0.1
            base_hip = 0.1 + profile.age * 0.05

        # BMI factor
        bmi = profile.weight_kg / ((profile.height_cm / 100) ** 2)
        if bmi < 19:
            bmi_factor = 1.5
        elif bmi < 25:
            bmi_factor = 1.0
        else:
            bmi_factor = 0.8

        major = base_major * bmi_factor
        hip = base_hip * bmi_factor

        # Risk factor multipliers
        if profile.family_history_hip_fracture:
            major *= 1.2; hip *= 1.5
        if profile.previous_fracture:
            major *= 1.8; hip *= 2.0
        if profile.smoker:
            major *= 1.2; hip *= 1.3
        if profile.alcohol_3_plus_units_daily:
            major *= 1.2; hip *= 1.2
        if profile.rheumatoid_arthritis:
            major *= 1.4; hip *= 1.5
        if profile.secondary_osteoporosis:
            major *= 1.3; hip *= 1.5

        # BMD T-score adjustment
        t = profile.femoral_neck_bmd_t_score
        if t <= -2.5:
            major *= 1.8; hip *= 2.5
            bmd_cat = "Osteoporosis"
        elif t <= -1.0:
            major *= 1.3; hip *= 1.5
            bmd_cat = "Osteopenia"
        else:
            bmd_cat = "Normal"

        major = min(99, major)
        hip = min(99, hip)

        # Risk level
        if major >= 20 or hip >= 3:
            risk = RiskLevel.HIGH
        elif major >= 10 or hip >= 1:
            risk = RiskLevel.MODERATE
        else:
            risk = RiskLevel.LOW

        treat = (risk == RiskLevel.HIGH or bmd_cat == "Osteoporosis" or
                 (risk == RiskLevel.MODERATE and bmd_cat == "Osteopenia" and profile.previous_fracture))

        recs = ["Calcium 1000-1200 mg/day", "Vitamin D 800-1000 IU/day", "Weight-bearing exercise", "Fall prevention assessment"]
        if treat:
            recs += ["Bisphosphonate (alendronate/risedronate) or denosumab", "Repeat DXA in 1-2 years"]
        if profile.smoker:
            recs.append("Smoking cessation")
        if profile.alcohol_3_plus_units_daily:
            recs.append("Alcohol reduction")
        if bmd_cat == "Osteoporosis":
            recs.append("Avoid glucocorticoids if possible; if needed, use lowest dose")

        return OsteoporosisResult(
            major_fracture_10yr_percent=round(major, 2),
            hip_fracture_10yr_percent=round(hip, 2),
            risk_level=risk,
            t_score_interpretation=f"T-score = {t} ({bmd_cat})" if t != 0 else "BMD not provided",
            bmd_category=bmd_cat,
            treatment_recommended=treat,
            recommendations=recs,
            follow_up="DXA every 1-2 years if treated; every 2-5 years if monitoring"
        )


def run():
    calc = OsteoporosisCalculator()

    print("=" * 60)
    print("Osteoporosis Risk Calculator")
    print("=" * 60)

    profile = OsteoporosisProfile(
        age=68, gender="female", weight_kg=55, height_cm=160,
        family_history_hip_fracture=True, previous_fracture=True,
        smoker=False, rheumatoid_arthritis=True,
        femoral_neck_bmd_t_score=-2.8
    )

    result = calc.calculate(profile)
    print(f"\nMajor fracture 10yr: {result.major_fracture_10yr_percent}%")
    print(f"Hip fracture 10yr: {result.hip_fracture_10yr_percent}%")
    print(f"Risk level: {result.risk_level.value}")
    print(f"BMD: {result.t_score_interpretation}")
    print(f"Treatment recommended: {result.treatment_recommended}")
    print(f"Recommendations: {result.recommendations}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
