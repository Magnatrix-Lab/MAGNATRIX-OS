"""
Skin Cancer Risk Assessment — Dermatology
Melanoma risk factors, UV exposure scoring, and prevention guidance.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class FitzpatrickSkinType(Enum):
    TYPE_I = 1    # Always burns, never tans
    TYPE_II = 2   # Usually burns, tans minimally
    TYPE_III = 3  # Sometimes burns, tans uniformly
    TYPE_IV = 4   # Burns minimally, tans well
    TYPE_V = 5    # Rarely burns, tans darkly
    TYPE_VI = 6   # Never burns, deeply pigmented


class RiskLevel(Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class SkinCancerProfile:
    age: int
    skin_type: FitzpatrickSkinType
    family_history_melanoma: bool = False
    personal_history_skin_cancer: bool = False
    total_moles: int = 0
    atypical_moles: int = 0
    severe_sunburns_history: int = 0
    tanning_bed_use: bool = False
    outdoor_occupation: bool = False
    latitude_of_residence: float = 40.0  # degrees
    altitude_meters: float = 0.0
    immunosuppressed: bool = False


@dataclass
class SkinCancerResult:
    melanoma_risk: RiskLevel
    non_melanoma_risk: RiskLevel
    risk_score: int
    max_score: int
    recommendations: List[str]
    screening_frequency: str
    notes: List[str]


class SkinCancerRiskCalculator:
    """Assess skin cancer risk based on established factors."""

    def calculate(self, profile: SkinCancerProfile) -> SkinCancerResult:
        score = 0
        notes = []

        # Age
        if profile.age < 20:
            score += 1
        elif profile.age < 40:
            score += 2
        elif profile.age < 60:
            score += 4
        else:
            score += 6

        # Skin type (lighter = higher risk)
        score += (7 - profile.skin_type.value) * 2

        # Family history
        if profile.family_history_melanoma:
            score += 5
            notes.append("Family history of melanoma doubles risk.")

        # Personal history
        if profile.personal_history_skin_cancer:
            score += 6
            notes.append("Previous skin cancer significantly increases recurrence risk.")

        # Moles
        if profile.total_moles > 100:
            score += 3
        elif profile.total_moles > 50:
            score += 2
        if profile.atypical_moles > 5:
            score += 4
        elif profile.atypical_moles > 0:
            score += 2

        # Sunburns
        score += min(profile.severe_sunburns_history, 5) * 2

        # Tanning beds
        if profile.tanning_bed_use:
            score += 4
            notes.append("Tanning bed use increases melanoma risk by ~75% before age 30.")

        # Outdoor occupation
        if profile.outdoor_occupation:
            score += 2

        # UV index proxy (latitude + altitude)
        uv_index = max(0, (50 - abs(profile.latitude_of_residence)) / 10 + profile.altitude_meters / 1000)
        if uv_index > 5:
            score += 3
        elif uv_index > 3:
            score += 1

        # Immunosuppression
        if profile.immunosuppressed:
            score += 5
            notes.append("Immunosuppression increases non-melanoma skin cancer risk 10-100x.")

        max_score = 50
        score = min(score, max_score)

        # Risk levels
        if score >= 30:
            melanoma_risk = RiskLevel.VERY_HIGH
            non_melanoma = RiskLevel.VERY_HIGH
        elif score >= 22:
            melanoma_risk = RiskLevel.HIGH
            non_melanoma = RiskLevel.HIGH
        elif score >= 14:
            melanoma_risk = RiskLevel.MODERATE
            non_melanoma = RiskLevel.MODERATE
        elif score >= 7:
            melanoma_risk = RiskLevel.LOW
            non_melanoma = RiskLevel.LOW
        else:
            melanoma_risk = RiskLevel.VERY_LOW
            non_melanoma = RiskLevel.VERY_LOW

        # Recommendations
        recs = ["Daily SPF 30+ broad-spectrum sunscreen", "Seek shade 10am-4pm", "Wear protective clothing"]
        if melanoma_risk.value in ["moderate", "high", "very_high"]:
            recs += ["Monthly self-skin examination", "Annual dermatologist skin check", "Photograph suspicious lesions"]
        if profile.tanning_bed_use:
            recs.append("Discontinue tanning bed use immediately")
        if profile.outdoor_occupation:
            recs.append("Reapply sunscreen every 2 hours when outdoors")

        screening = "Annual" if melanoma_risk.value in ["moderate", "high", "very_high"] else "Every 2-3 years"
        if melanoma_risk == RiskLevel.VERY_HIGH:
            screening = "Every 6 months"

        return SkinCancerResult(
            melanoma_risk=melanoma_risk,
            non_melanoma_risk=non_melanoma,
            risk_score=score,
            max_score=max_score,
            recommendations=recs,
            screening_frequency=screening,
            notes=notes
        )

    def uv_index_exposure(self, uv_index: float, minutes_exposed: int, spf: int) -> dict:
        """Estimate effective UV dose."""
        effective_dose = uv_index * minutes_exposed / (spf if spf > 0 else 1)
        burn_threshold = 200  # arbitrary units for sunburn
        return {
            "uv_index": uv_index,
            "minutes_exposed": minutes_exposed,
            "spf": spf,
            "effective_dose": round(effective_dose, 1),
            "burn_risk": "High" if effective_dose > burn_threshold else "Moderate" if effective_dose > burn_threshold / 2 else "Low",
        }


def run():
    calc = SkinCancerRiskCalculator()

    print("=" * 60)
    print("Skin Cancer Risk Assessment")
    print("=" * 60)

    profile = SkinCancerProfile(
        age=45, skin_type=FitzpatrickSkinType.TYPE_II,
        family_history_melanoma=True,
        total_moles=80, atypical_moles=3,
        severe_sunburns_history=4,
        tanning_bed_use=True,
        outdoor_occupation=True,
        latitude_of_residence=35.0
    )

    result = calc.calculate(profile)
    print(f"\nRisk Score: {result.risk_score}/{result.max_score}")
    print(f"Melanoma Risk: {result.melanoma_risk.value}")
    print(f"Non-Melanoma Risk: {result.non_melanoma_risk.value}")
    print(f"Screening: {result.screening_frequency}")
    print(f"Recommendations: {result.recommendations}")
    print(f"Notes: {result.notes}")

    uv = calc.uv_index_exposure(8, 120, 30)
    print(f"\nUV Exposure: {uv}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
