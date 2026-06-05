"""
Cancer Risk Assessment — Oncology
Gail model-inspired breast cancer risk and general cancer risk factors.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class RiskLevel(Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    AVERAGE = "average"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class CancerRiskProfile:
    age: int
    gender: str
    family_history_breast: bool = False
    family_history_ovarian: bool = False
    family_history_colorectal: bool = False
    family_history_lung: bool = False
    family_history_pancreatic: bool = False
    personal_history_cancer: bool = False
    smoking_pack_years: float = 0.0
    alcohol_drinks_per_week: int = 0
    bmi: float = 22.0
    physical_activity_minutes_per_week: int = 0
    red_meat_servings_per_week: int = 0
    processed_meat_servings_per_week: int = 0
    fiber_intake_g_day: float = 0.0
    sun_exposure_hours_per_week: float = 0.0
    asbestos_exposure: bool = False
    radon_exposure: bool = False
    hpv_positive: bool = False
    hepatitis_b_or_c: bool = False
    h_pylori_positive: bool = False
    genetic_mutation: str = ""  # BRCA1, BRCA2, Lynch, etc.


@dataclass
class CancerRiskResult:
    overall_risk: RiskLevel
    breast_cancer_risk: str
    colorectal_cancer_risk: str
    lung_cancer_risk: str
    prostate_cancer_risk: str
    skin_cancer_risk: str
    screening_recommendations: List[str]
    lifestyle_recommendations: List[str]
    genetic_counseling: bool
    notes: List[str]


class CancerRiskCalculator:
    """Multi-cancer risk assessment with screening guidance."""

    def calculate(self, profile: CancerRiskProfile) -> CancerRiskResult:
        notes = []
        score = 0

        # Age factor
        if profile.age < 40:
            score += 1
        elif profile.age < 50:
            score += 2
        elif profile.age < 60:
            score += 4
        elif profile.age < 70:
            score += 6
        else:
            score += 8

        # Family history
        fh_count = sum([profile.family_history_breast, profile.family_history_ovarian,
                       profile.family_history_colorectal, profile.family_history_lung,
                       profile.family_history_pancreatic])
        score += fh_count * 3
        if fh_count >= 2:
            notes.append("Multiple family cancers — consider genetic testing panel.")

        # Personal history
        if profile.personal_history_cancer:
            score += 5
            notes.append("Personal cancer history increases second primary risk.")

        # Smoking
        if profile.smoking_pack_years > 0:
            score += min(int(profile.smoking_pack_years), 10)
            if profile.smoking_pack_years >= 20:
                notes.append("Heavy smoking history — lung cancer screening indicated.")

        # Alcohol
        if profile.alcohol_drinks_per_week > 7:
            score += 2
            if profile.gender.lower() == "female" and profile.alcohol_drinks_per_week > 14:
                notes.append("High alcohol intake increases breast cancer risk.")

        # BMI
        if profile.bmi >= 30:
            score += 3
            notes.append("Obesity increases multiple cancer risks.")
        elif profile.bmi >= 25:
            score += 1

        # Physical inactivity
        if profile.physical_activity_minutes_per_week < 150:
            score += 2

        # Diet
        if profile.red_meat_servings_per_week > 3:
            score += 1
        if profile.processed_meat_servings_per_week > 1:
            score += 2
        if profile.fiber_intake_g_day < 20:
            score += 1

        # Infections
        if profile.hpv_positive:
            score += 2
            notes.append("HPV positive — cervical/anal/oropharyngeal cancer risk.")
        if profile.hepatitis_b_or_c:
            score += 3
            notes.append("Hepatitis B/C — hepatocellular carcinoma screening.")
        if profile.h_pylori_positive:
            score += 1
            notes.append("H. pylori — gastric cancer risk, treat if symptomatic.")

        # Environmental
        if profile.asbestos_exposure:
            score += 3
            notes.append("Asbestos exposure — mesothelioma risk.")
        if profile.radon_exposure:
            score += 2

        # Genetic
        if profile.genetic_mutation:
            score += 10
            notes.append(f"Known mutation {profile.genetic_mutation} — intensive surveillance.")

        # Risk level
        if score >= 25:
            overall = RiskLevel.VERY_HIGH
        elif score >= 18:
            overall = RiskLevel.HIGH
        elif score >= 12:
            overall = RiskLevel.MODERATE
        elif score >= 6:
            overall = RiskLevel.AVERAGE
        elif score >= 3:
            overall = RiskLevel.LOW
        else:
            overall = RiskLevel.VERY_LOW

        # Site-specific risks
        breast = "High" if (profile.family_history_breast or profile.genetic_mutation in ["BRCA1", "BRCA2"]) else "Average"
        colorectal = "High" if (profile.family_history_colorectal or profile.genetic_mutation == "Lynch") else "Average"
        lung = "High" if profile.smoking_pack_years >= 20 else "Average"
        prostate = "High" if profile.age > 50 and profile.gender.lower() == "male" else "Average"
        skin = "High" if profile.sun_exposure_hours_per_week > 10 else "Average"

        # Screening
        screening = ["Annual physical with age-appropriate cancer screening"]
        if profile.gender.lower() == "female" and profile.age >= 40:
            screening.append("Mammography every 1-2 years")
        if profile.age >= 45:
            screening.append("Colorectal cancer screening (colonoscopy every 10 years or FIT annually)")
        if profile.smoking_pack_years >= 20 and profile.age >= 50:
            screening.append("Low-dose CT chest annually for lung cancer")
        if profile.age >= 50 and profile.gender.lower() == "male":
            screening.append("Prostate cancer screening discussion (PSA)")
        if profile.hepatitis_b_or_c:
            screening.append("HCC surveillance (ultrasound + AFP every 6 months)")
        if profile.genetic_mutation:
            screening.append("Genetic counseling + mutation-specific surveillance protocol")

        lifestyle = ["Maintain healthy weight", "150 min/week exercise", "Balanced diet rich in fruits/vegetables", "Limit alcohol", "Sun protection"]
        if profile.smoking_pack_years > 0:
            lifestyle.append("Smoking cessation immediately")

        genetic = bool(profile.genetic_mutation) or fh_count >= 2

        return CancerRiskResult(
            overall_risk=overall,
            breast_cancer_risk=breast,
            colorectal_cancer_risk=colorectal,
            lung_cancer_risk=lung,
            prostate_cancer_risk=prostate,
            skin_cancer_risk=skin,
            screening_recommendations=screening,
            lifestyle_recommendations=lifestyle,
            genetic_counseling=genetic,
            notes=notes
        )


def run():
    calc = CancerRiskCalculator()

    print("=" * 60)
    print("Cancer Risk Assessment")
    print("=" * 60)

    profile = CancerRiskProfile(
        age=55, gender="female", family_history_breast=True, family_history_ovarian=True,
        smoking_pack_years=0, bmi=28, alcohol_drinks_per_week=10,
        physical_activity_minutes_per_week=60, genetic_mutation="BRCA1"
    )

    result = calc.calculate(profile)
    print(f"\nOverall risk: {result.overall_risk.value}")
    print(f"Breast: {result.breast_cancer_risk}, Colorectal: {result.colorectal_cancer_risk}")
    print(f"Lung: {result.lung_cancer_risk}, Prostate: {result.prostate_cancer_risk}")
    print(f"Skin: {result.skin_cancer_risk}")
    print(f"Screening: {result.screening_recommendations}")
    print(f"Lifestyle: {result.lifestyle_recommendations}")
    print(f"Genetic counseling: {result.genetic_counseling}")
    print(f"Notes: {result.notes}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
