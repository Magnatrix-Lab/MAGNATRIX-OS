"""
Coagulation Calculator — Hematology
INR, warfarin dosing, and bleeding risk assessment.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List, Dict
from enum import Enum


class Indication(Enum):
    AFIB = "atrial_fibrillation"
    DVT_PE = "dvt_pe"
    MECHANICAL_VALVE = "mechanical_valve"
    POST_MI = "post_mi"
    RECURRENT_VTE = "recurrent_vte"


@dataclass
class CoagulationProfile:
    indication: Indication
    current_inr: float
    target_inr_low: float = 2.0
    target_inr_high: float = 3.0
    patient_age: int = 65
    liver_disease: bool = False
    interacting_drugs: List[str] = None
    diet_vitamin_k_consistent: bool = True
    previous_bleeding: bool = False
    platelets_k_u_l: float = 250.0

    def __post_init__(self):
        if self.interacting_drugs is None:
            self.interacting_drugs = []


@dataclass
class CoagulationResult:
    inr_status: str
    warfarin_adjustment: str
    bleed_risk_score: int
    bleed_risk_category: str
    next_inr_check: str
    recommendations: List[str]


class CoagulationCalculator:
    """Warfarin/INR management and bleeding risk assessment."""

    def calculate(self, profile: CoagulationProfile) -> CoagulationResult:
        # INR status
        if profile.current_inr < profile.target_inr_low * 0.7:
            status = "Subtherapeutic — high thrombosis risk"
            adjustment = "Increase weekly dose by 5-10% or give 1-2mg booster"
            check = "Recheck INR in 3-7 days"
        elif profile.current_inr < profile.target_inr_low:
            status = "Low therapeutic range"
            adjustment = "Minor increase (5%) or maintain if stable trend"
            check = "Recheck in 1-2 weeks"
        elif profile.current_inr <= profile.target_inr_high:
            status = "Therapeutic"
            adjustment = "No change"
            check = "Recheck in 4-12 weeks (stable patients)"
        elif profile.current_inr <= profile.target_inr_high * 1.5:
            status = "Supratherapeutic"
            adjustment = "Hold 1 dose then reduce by 5-10%"
            check = "Recheck in 3-5 days"
        else:
            status = "Critically elevated"
            adjustment = "Hold warfarin, vitamin K 2.5-5mg PO if >6.0 or bleeding"
            check = "Recheck in 24 hours"

        # HAS-BLED (simplified) — rough bleeding risk
        bleed_score = 0
        if profile.patient_age > 65:
            bleed_score += 1
        if profile.previous_bleeding:
            bleed_score += 2
        if profile.liver_disease:
            bleed_score += 2
        if len(profile.interacting_drugs) > 0:
            bleed_score += 1
        if not profile.diet_vitamin_k_consistent:
            bleed_score += 1
        if profile.platelets_k_u_l < 150:
            bleed_score += 1

        if bleed_score >= 5:
            bleed_risk = "High bleeding risk"
        elif bleed_score >= 3:
            bleed_risk = "Moderate bleeding risk"
        else:
            bleed_risk = "Low bleeding risk"

        recs = ["Consistent vitamin K intake", "Avoid NSAIDs", "Monitor for bruising, melena, hematuria"]
        if profile.liver_disease:
            recs.append("Liver disease — consider DOAC instead of warfarin if possible")
        if bleed_score >= 3:
            recs.append("High bleeding risk — ensure INR kept in lower therapeutic range")
        if profile.interacting_drugs:
            recs.append(f"Drug interactions: {profile.interacting_drugs} — monitor closely")

        return CoagulationResult(
            inr_status=status,
            warfarin_adjustment=adjustment,
            bleed_risk_score=bleed_score,
            bleed_risk_category=bleed_risk,
            next_inr_check=check,
            recommendations=recs
        )

    def bridge_to_warfarin(self, heparin_dose_units: float, weight_kg: float) -> dict:
        """Bridging protocol for warfarin initiation."""
        # LMWH bridge until INR therapeutic x 2 days
        return {
            "enoxaparin_mg": round(1.0 * weight_kg, 1),  # 1 mg/kg BID
            "start_warfarin_load": "5mg daily for 2 days, then adjust by INR",
            "overlap_duration": "Continue LMWH until INR therapeutic x 48 hours",
            "first_inr_check": "Day 3-4 after starting warfarin"
        }


def run():
    calc = CoagulationCalculator()

    print("=" * 60)
    print("Coagulation Calculator")
    print("=" * 60)

    profile = CoagulationProfile(
        indication=Indication.AFIB, current_inr=1.4,
        target_inr_low=2.0, target_inr_high=3.0,
        patient_age=72, previous_bleeding=True,
        interacting_drugs=["amiodarone"], platelets_k_u_l=180
    )

    result = calc.calculate(profile)
    print(f"\nINR status: {result.inr_status}")
    print(f"Adjustment: {result.warfarin_adjustment}")
    print(f"Bleed score: {result.bleed_risk_score} ({result.bleed_risk_category})")
    print(f"Next check: {result.next_inr_check}")
    print(f"Recommendations: {result.recommendations}")

    print(f"\nBridge protocol: {calc.bridge_to_warfarin(4000, 70)}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
