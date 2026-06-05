"""
Melanoma ABCDE Calculator — Dermatology
Asymmetry, Border, Color, Diameter, Evolution assessment for pigmented lesions.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class RiskLevel(Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class MelanomaProfile:
    asymmetry: bool        # One half unlike the other
    border_irregular: bool # Ragged, notched, blurred
    color_variegated: bool # Multiple colors (brown, black, tan, red, white, blue)
    diameter_mm: float     # >6mm is concerning
    evolving: bool          # Changing in size, shape, color, elevation
    itching: bool = False
    bleeding: bool = False
    elevation: bool = False  # Raised above skin surface
    ulceration: bool = False
    family_history: bool = False
    personal_history: bool = False
    new_lesion_after_age_40: bool = False


@dataclass
class MelanomaResult:
    abcde_score: int
    risk_level: RiskLevel
    dermoscopy_recommended: bool
    biopsy_recommended: bool
    urgency: str
    differential_diagnosis: List[str]
    notes: List[str]


class MelanomaABCDECalculator:
    """ABCDE rule for melanoma detection."""

    def calculate(self, profile: MelanomaProfile) -> MelanomaResult:
        score = 0
        notes = []

        if profile.asymmetry:
            score += 1
            notes.append("Asymmetry present")
        if profile.border_irregular:
            score += 1
            notes.append("Border irregularity present")
        if profile.color_variegated:
            score += 1
            notes.append("Color variegation present")
        if profile.diameter_mm > 6:
            score += 1
            notes.append(f"Diameter >6mm ({profile.diameter_mm}mm)")
        if profile.evolving:
            score += 1
            notes.append("Evolution documented")

        # Extended features
        if profile.itching:
            score += 1
            notes.append("Itching — concerning symptom")
        if profile.bleeding:
            score += 1
            notes.append("Bleeding — concerning symptom")
        if profile.elevation:
            score += 1
            notes.append("Elevation present")
        if profile.ulceration:
            score += 2
            notes.append("Ulceration — high-risk feature")
        if profile.family_history:
            score += 1
        if profile.personal_history:
            score += 2
        if profile.new_lesion_after_age_40:
            score += 1
            notes.append("New lesion after age 40 warrants evaluation")

        max_score = 13

        if score >= 7:
            risk = RiskLevel.VERY_HIGH
            urgency = "Urgent dermatology within 1-2 weeks"
        elif score >= 5:
            risk = RiskLevel.HIGH
            urgency = "Dermatology referral within 2-4 weeks"
        elif score >= 3:
            risk = RiskLevel.MODERATE
            urgency = "Schedule dermatology within 4-6 weeks"
        else:
            risk = RiskLevel.LOW
            urgency = "Routine monitoring, photograph for comparison"

        dermoscopy = score >= 2
        biopsy = score >= 4

        differential = ["Seborrheic keratosis", "Atypical nevus", "Pigmented basal cell carcinoma"]
        if profile.diameter_mm > 6 and profile.color_variegated:
            differential = ["Melanoma (primary concern)", "Atypical nevus", "Spitz nevus", "Blue nevus"]

        return MelanomaResult(
            abcde_score=score,
            risk_level=risk,
            dermoscopy_recommended=dermoscopy,
            biopsy_recommended=biopsy,
            urgency=urgency,
            differential_diagnosis=differential,
            notes=notes
        )


def run():
    calc = MelanomaABCDECalculator()

    print("=" * 60)
    print("Melanoma ABCDE Calculator")
    print("=" * 60)

    profile = MelanomaProfile(
        asymmetry=True, border_irregular=True, color_variegated=True,
        diameter_mm=8.5, evolving=True, itching=True, bleeding=False,
        elevation=True, ulceration=False, family_history=True
    )

    result = calc.calculate(profile)
    print(f"\nABCDE Score: {result.abcde_score}")
    print(f"Risk: {result.risk_level.value}")
    print(f"Dermoscopy: {result.dermoscopy_recommended}")
    print(f"Biopsy: {result.biopsy_recommended}")
    print(f"Urgency: {result.urgency}")
    print(f"Differential: {result.differential_diagnosis}")
    print(f"Notes: {result.notes}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
