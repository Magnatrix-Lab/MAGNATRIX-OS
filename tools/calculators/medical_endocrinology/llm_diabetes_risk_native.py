"""
Diabetes Risk Calculator — Endocrinology
Type 2 diabetes risk scoring (ADA + Finnish Diabetes Risk Score hybrid).
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class RiskLevel(Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class DiabetesProfile:
    age: int
    bmi: float
    waist_cm: float
    gender: str  # "male" or "female"
    family_history_diabetes: bool = False
    hypertension: bool = False
    physical_activity_minutes_per_week: int = 0
    diet_quality_score: int = 5  # 1-10 (higher = better)
    gestational_diabetes_history: bool = False  # Female only
    polycystic_ovary: bool = False  # Female only
    ethnicity_high_risk: bool = False  # African, Hispanic, Native American, Asian, Pacific Islander
    fasting_glucose_mg_dl: float = 0.0
    hba1c_percent: float = 0.0


@dataclass
class DiabetesResult:
    risk_score: int
    max_score: int
    risk_level: RiskLevel
    ten_year_risk_percent: float
    recommendations: List[str]
    screening_interval: str
    prediabetes: bool
    notes: List[str]


class DiabetesRiskCalculator:
    """Diabetes risk assessment with ADA and modified FINDRISC scoring."""

    def calculate(self, profile: DiabetesProfile) -> DiabetesResult:
        score = 0
        notes = []

        # Age
        if profile.age < 45:
            score += 0
        elif profile.age < 54:
            score += 2
        elif profile.age < 64:
            score += 4
        else:
            score += 6

        # BMI
        if profile.bmi < 25:
            score += 0
        elif profile.bmi < 30:
            score += 3
        else:
            score += 5

        # Waist
        if profile.gender.lower() == "male":
            if profile.waist_cm >= 102:
                score += 4
            elif profile.waist_cm >= 94:
                score += 3
        else:
            if profile.waist_cm >= 88:
                score += 4
            elif profile.waist_cm >= 80:
                score += 3

        # Family history
        if profile.family_history_diabetes:
            score += 5

        # Hypertension
        if profile.hypertension:
            score += 2

        # Physical activity
        if profile.physical_activity_minutes_per_week < 150:
            score += 2
        elif profile.physical_activity_minutes_per_week < 30:
            score += 4

        # Diet
        if profile.diet_quality_score <= 4:
            score += 2

        # Female-specific
        if profile.gender.lower() == "female":
            if profile.gestational_diabetes_history:
                score += 5
                notes.append("History of gestational diabetes significantly increases T2D risk.")
            if profile.polycystic_ovary:
                score += 3

        # Ethnicity
        if profile.ethnicity_high_risk:
            score += 3

        # Biomarkers (override if available)
        prediabetes = False
        if profile.fasting_glucose_mg_dl > 0:
            if 100 <= profile.fasting_glucose_mg_dl < 126:
                prediabetes = True
                notes.append(f"Fasting glucose {profile.fasting_glucose_mg_dl} mg/dL indicates prediabetes.")
            elif profile.fasting_glucose_mg_dl >= 126:
                prediabetes = True
                notes.append(f"Fasting glucose {profile.fasting_glucose_mg_dl} mg/dL — diabetes threshold met.")
        if profile.hba1c_percent > 0:
            if 5.7 <= profile.hba1c_percent < 6.5:
                prediabetes = True
                notes.append(f"HbA1c {profile.hba1c_percent}% indicates prediabetes.")
            elif profile.hba1c_percent >= 6.5:
                prediabetes = True
                notes.append(f"HbA1c {profile.hba1c_percent}% — diabetes threshold met.")

        max_score = 40
        score = min(score, max_score)

        # Risk level
        if score >= 18:
            risk = RiskLevel.VERY_HIGH
            ten_year = 50.0
        elif score >= 12:
            risk = RiskLevel.HIGH
            ten_year = 30.0
        elif score >= 7:
            risk = RiskLevel.MODERATE
            ten_year = 15.0
        elif score >= 3:
            risk = RiskLevel.LOW
            ten_year = 5.0
        else:
            risk = RiskLevel.VERY_LOW
            ten_year = 1.0

        recs = ["Maintain healthy weight", "150 min/week moderate exercise", "High-fiber, low-sugar diet"]
        if risk.value in ["moderate", "high", "very_high"]:
            recs += ["Annual fasting glucose or HbA1c screening", "Consider metformin if prediabetes + BMI > 35 + age < 60"]
        if prediabetes:
            recs += ["Diabetes Prevention Program (DPP) enrollment", "Target 7% weight loss if overweight"]
        if profile.bmi >= 30:
            recs.append("Weight management program — target 5-10% loss")

        screening = "Annual" if risk.value in ["moderate", "high", "very_high"] else "Every 3 years"

        return DiabetesResult(
            risk_score=score,
            max_score=max_score,
            risk_level=risk,
            ten_year_risk_percent=round(ten_year, 1),
            recommendations=recs,
            screening_interval=screening,
            prediabetes=prediabetes,
            notes=notes
        )


def run():
    calc = DiabetesRiskCalculator()

    print("=" * 60)
    print("Diabetes Risk Calculator")
    print("=" * 60)

    profile = DiabetesProfile(
        age=52, bmi=31.5, waist_cm=102, gender="male",
        family_history_diabetes=True, hypertension=True,
        physical_activity_minutes_per_week=30,
        diet_quality_score=4, ethnicity_high_risk=True,
        fasting_glucose_mg_dl=108, hba1c_percent=5.9
    )

    result = calc.calculate(profile)
    print(f"\nScore: {result.risk_score}/{result.max_score}")
    print(f"Risk: {result.risk_level.value}")
    print(f"10-year risk: {result.ten_year_risk_percent}%")
    print(f"Prediabetes: {result.prediabetes}")
    print(f"Screening: {result.screening_interval}")
    print(f"Recommendations: {result.recommendations}")
    print(f"Notes: {result.notes}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
