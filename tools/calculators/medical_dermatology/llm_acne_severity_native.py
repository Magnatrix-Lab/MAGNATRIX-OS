"""
Acne Severity Calculator — Dermatology
GAGS (Global Acne Grading System) and treatment recommendations.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List, Dict
from enum import Enum


class AcneSeverity(Enum):
    CLEAR = "clear"
    ALMOST_CLEAR = "almost_clear"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    VERY_SEVERE = "very_severe"


@dataclass
class AcneProfile:
    # Count of lesions by type and location
    forehead_comedones: int = 0
    forehead_papules: int = 0
    forehead_pustules: int = 0
    forehead_nodules: int = 0

    right_cheek_comedones: int = 0
    right_cheek_papules: int = 0
    right_cheek_pustules: int = 0
    right_cheek_nodules: int = 0

    left_cheek_comedones: int = 0
    left_cheek_papules: int = 0
    left_cheek_pustules: int = 0
    left_cheek_nodules: int = 0

    nose_comedones: int = 0
    nose_papules: int = 0
    nose_pustules: int = 0
    nose_nodules: int = 0

    chin_comedones: int = 0
    chin_papules: int = 0
    chin_pustules: int = 0
    chin_nodules: int = 0

    back_chest_comedones: int = 0
    back_chest_papules: int = 0
    back_chest_pustules: int = 0
    back_chest_nodules: int = 0

    duration_months: int = 0
    scarring_present: bool = False
    previous_treatments: List[str] = None

    def __post_init__(self):
        if self.previous_treatments is None:
            self.previous_treatments = []


@dataclass
class AcneResult:
    gags_score: float
    lesion_count: int
    severity: AcneSeverity
    treatment_plan: List[str]
    follow_up_weeks: int
    notes: List[str]


class AcneSeverityCalculator:
    """Global Acne Grading System (GAGS) calculator."""

    # GAGS factors: comedone=1, papule=2, pustule=3, nodule=4
    # Location factors: forehead=2, each cheek=2, nose=1, chin=1, back/chest=3
    FACTORS = {
        "comedone": 1, "papule": 2, "pustule": 3, "nodule": 4
    }
    LOCATION = {
        "forehead": 2, "right_cheek": 2, "left_cheek": 2, "nose": 1, "chin": 1, "back_chest": 3
    }

    def calculate(self, profile: AcneProfile) -> AcneResult:
        locations = {
            "forehead": (profile.forehead_comedones, profile.forehead_papules, profile.forehead_pustules, profile.forehead_nodules),
            "right_cheek": (profile.right_cheek_comedones, profile.right_cheek_papules, profile.right_cheek_pustules, profile.right_cheek_nodules),
            "left_cheek": (profile.left_cheek_comedones, profile.left_cheek_papules, profile.left_cheek_pustules, profile.left_cheek_nodules),
            "nose": (profile.nose_comedones, profile.nose_papules, profile.nose_pustules, profile.nose_nodules),
            "chin": (profile.chin_comedones, profile.chin_papules, profile.chin_pustules, profile.chin_nodules),
            "back_chest": (profile.back_chest_comedones, profile.back_chest_papules, profile.back_chest_pustules, profile.back_chest_nodules),
        }

        total_score = 0
        total_lesions = 0

        for loc, (com, pap, pus, nod) in locations.items():
            loc_factor = self.LOCATION[loc]
            score = (com * self.FACTORS["comedone"] + pap * self.FACTORS["papule"] +
                     pus * self.FACTORS["pustule"] + nod * self.FACTORS["nodule"]) * loc_factor
            total_score += score
            total_lesions += com + pap + pus + nod

        # Severity classification
        if total_score == 0:
            severity = AcneSeverity.CLEAR
        elif total_score <= 5:
            severity = AcneSeverity.ALMOST_CLEAR
        elif total_score <= 18:
            severity = AcneSeverity.MILD
        elif total_score <= 30:
            severity = AcneSeverity.MODERATE
        elif total_score <= 44:
            severity = AcneSeverity.SEVERE
        else:
            severity = AcneSeverity.VERY_SEVERE

        # Treatment plan
        treatments = []
        if severity in [AcneSeverity.CLEAR, AcneSeverity.ALMOST_CLEAR]:
            treatments = ["Gentle cleanser", "Moisturizer", "Maintenance topical retinoid (optional)"]
        elif severity == AcneSeverity.MILD:
            treatments = ["Topical retinoid (adapalene/tretinoin)", "Topical benzoyl peroxide 2.5-5%", "Gentle cleanser"]
        elif severity == AcneSeverity.MODERATE:
            treatments = ["Topical retinoid + benzoyl peroxide", "Topical or oral antibiotic (doxycycline/minocycline)", "Consider hormonal therapy if female"]
        elif severity == AcneSeverity.SEVERE:
            treatments = ["Oral isotretinoin (refer dermatology)", "Oral antibiotic + topical retinoid", "Hormonal therapy if female", "Intralesional steroids for nodules"]
        else:
            treatments = ["Urgent dermatology referral", "Oral isotretinoin", "Systemic corticosteroids if fulminant", "Psychological support"]

        if profile.scarring_present:
            treatments.append("Scar management: microneedling, laser, chemical peels")

        follow_up = 12 if severity.value in ["severe", "very_severe"] else 8 if severity == AcneSeverity.MODERATE else 4

        notes = [f"Total lesions: {total_lesions}", f"GAGS score: {total_score}"]
        if profile.duration_months > 6 and severity.value in ["moderate", "severe", "very_severe"]:
            notes.append("Persistent acne >6 months — consider isotretinoin earlier.")

        return AcneResult(
            gags_score=total_score,
            lesion_count=total_lesions,
            severity=severity,
            treatment_plan=treatments,
            follow_up_weeks=follow_up,
            notes=notes
        )


def run():
    calc = AcneSeverityCalculator()

    print("=" * 60)
    print("Acne Severity Calculator (GAGS)")
    print("=" * 60)

    profile = AcneProfile(
        forehead_comedones=5, forehead_papules=3, forehead_pustules=1,
        right_cheek_comedones=8, right_cheek_papules=5, right_cheek_pustules=2,
        left_cheek_comedones=6, left_cheek_papules=4, left_cheek_pustules=1,
        nose_comedones=10, nose_papules=2,
        chin_comedones=4, chin_papules=3, chin_pustules=2,
        duration_months=8, scarring_present=True
    )

    result = calc.calculate(profile)
    print(f"\nGAGS Score: {result.gags_score}")
    print(f"Severity: {result.severity.value}")
    print(f"Lesions: {result.lesion_count}")
    print(f"Treatment: {result.treatment_plan}")
    print(f"Follow-up: {result.follow_up_weeks} weeks")
    print(f"Notes: {result.notes}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
