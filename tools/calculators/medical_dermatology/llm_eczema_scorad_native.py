"""
Eczema Severity Calculator — Dermatology
SCORAD (SCORing Atopic Dermatitis) index calculator.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class EczemaProfile:
    extent_percent: float  # 0-100% body surface
    intensity_items: dict  # redness, swelling, oozing, crusting, lichenification, dryness
    # Each scored 0-3
    pruritus_score: int  # 0-10 (patient-reported)
    sleep_loss_score: int  # 0-10


@dataclass
class EczemaResult:
    scorad_score: float
    severity: str
    objective_score: float
    subjective_score: float
    recommendations: List[str]


class EczemaCalculator:
    """SCORAD index calculator for atopic dermatitis."""

    def calculate(self, profile: EczemaProfile) -> EczemaResult:
        # Validate intensity items
        default_items = {"redness": 0, "swelling": 0, "oozing": 0, "crusting": 0, "lichenification": 0, "dryness": 0}
        items = {**default_items, **profile.intensity_items}
        intensity_sum = sum(min(max(v, 0), 3) for v in items.values())

        # SCORAD formula: A/5 + 7B/2 + C
        # A = extent (0-100), B = intensity sum (0-18), C = pruritus + sleep loss (0-20)
        a = min(max(profile.extent_percent, 0), 100)
        b = intensity_sum
        c = min(max(profile.pruritus_score, 0), 10) + min(max(profile.sleep_loss_score, 0), 10)

        objective = a / 5 + 7 * b / 2
        subjective = c
        scorad = objective + subjective

        if scorad < 15:
            severity = "Clear / Mild"
        elif scorad < 40:
            severity = "Moderate"
        elif scorad < 70:
            severity = "Severe"
        else:
            severity = "Very Severe"

        recs = ["Emollient therapy (apply liberally 2-3x daily)", "Avoid irritants and allergens"]
        if scorad >= 15:
            recs.append("Topical corticosteroid ( potency matched to severity )")
        if scorad >= 40:
            recs += ["Topical calcineurin inhibitor (tacrolimus/pimecrolimus)", "Wet wrap therapy", "Phototherapy consideration"]
        if scorad >= 70:
            recs += ["Systemic therapy (dupilumab, JAK inhibitor, cyclosporine)", "Dermatology referral", "Infection screening"]
        if profile.sleep_loss_score >= 5:
            recs.append("Address sleep disturbance — consider sedating antihistamine at night")

        return EczemaResult(
            scorad_score=round(scorad, 2),
            severity=severity,
            objective_score=round(objective, 2),
            subjective_score=round(subjective, 2),
            recommendations=recs
        )


def run():
    calc = EczemaCalculator()

    print("=" * 60)
    print("Eczema SCORAD Calculator")
    print("=" * 60)

    profile = EczemaProfile(
        extent_percent=25,
        intensity_items={"redness": 2, "swelling": 1, "oozing": 1, "crusting": 2, "lichenification": 2, "dryness": 3},
        pruritus_score=7,
        sleep_loss_score=4
    )

    result = calc.calculate(profile)
    print(f"\nSCORAD: {result.scorad_score}")
    print(f"Severity: {result.severity}")
    print(f"Objective: {result.objective_score}, Subjective: {result.subjective_score}")
    print(f"Recommendations: {result.recommendations}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
