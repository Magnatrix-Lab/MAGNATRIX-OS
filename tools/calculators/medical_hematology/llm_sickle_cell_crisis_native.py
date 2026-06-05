"""
Sickle Cell Crisis Calculator — Hematology
Pain crisis risk, transfusion needs, and hydroxyurea dosing.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class CrisisType(Enum):
    VASO_OCCLUSIVE = "vaso_occlusive"
    ACUTE_CHEST = "acute_chest"
    SPLENIC_SEQUESTRATION = "splenic_sequestration"
    PRIAPISM = "priapism"
    STROKE = "stroke"
    APLASTIC = "aplastic"


@dataclass
class SickleCellProfile:
    hemoglobin_g_dl: float
    hemoglobin_s_percent: float
    hemoglobin_f_percent: float
    wbc_k_u_l: float
    platelets_k_u_l: float
    ldh_u_l: float
    bilirubin_mg_dl: float
    creatinine_mg_dl: float
    crisis_type: CrisisType
    pain_score: int = 0  # 0-10
    oxygen_saturation: float = 98.0
    fever_present: bool = False
    previous_strokes: int = 0
    on_hydroxyurea: bool = False
    hydroxyurea_dose_mg_kg: float = 0.0


@dataclass
class SickleCellResult:
    severity: str
    exchange_transfusion_indicated: bool
    simple_transfusion_indicated: bool
    transfusion_target_hgb_s_percent: float
    pain_management: List[str]
    iv_hydration: bool
    oxygen_needed: bool
    antibiotics_needed: bool
    hydroxyurea_adjustment: str
    follow_up: str


class SickleCellCalculator:
    """Sickle cell crisis management calculator."""

    def calculate(self, profile: SickleCellProfile) -> SickleCellResult:
        crisis = profile.crisis_type
        exchange = False
        simple = False
        target_hgb_s = 0.0
        pain_mgmt = []
        iv_hydration = True
        oxygen = False
        antibiotics = False
        hydroxy_adj = "Continue current dose"

        if crisis == CrisisType.VASO_OCCLUSIVE:
            severity = "Moderate" if profile.pain_score < 7 else "Severe"
            pain_mgmt = ["IV opioids (morphine/hydromorphone) — PCA preferred", "Ketorolac if no contraindication", "Warm compresses", "Non-pharmacological: distraction, relaxation"]
            exchange = False
            simple = profile.hemoglobin_g_dl < 5.0
            target_hgb_s = 30.0

        elif crisis == CrisisType.ACUTE_CHEST:
            severity = "Severe"
            oxygen = True
            antibiotics = True
            exchange = True
            target_hgb_s = 30.0
            pain_mgmt = ["Incentive spirometry", "Pain control to allow deep breathing"]
            iv_hydration = True

        elif crisis == CrisisType.SPLENIC_SEQUESTRATION:
            severity = "Severe"
            simple = True
            target_hgb_s = 30.0
            pain_mgmt = ["Splenic protection", "Monitor for hypovolemia"]
            iv_hydration = True

        elif crisis == CrisisType.PRIAPISM:
            severity = "Severe" if profile.pain_score > 5 else "Moderate"
            pain_mgmt = ["Aspiration + irrigation if > 4 hours", "Phenylephrine injection", "Urology consultation"]
            exchange = profile.pain_score > 5 and profile.hemoglobin_s_percent > 50
            target_hgb_s = 30.0

        elif crisis == CrisisType.STROKE:
            severity = "Critical"
            exchange = True
            target_hgb_s = 30.0
            pain_mgmt = ["Neurology + stroke team activation", "Supportive care"]
            oxygen = profile.oxygen_saturation < 94

        elif crisis == CrisisType.APLASTIC:
            severity = "Severe"
            simple = True
            pain_mgmt = ["Supportive care", "Infection prophylaxis"]
            antibiotics = profile.fever_present

        else:
            severity = "Unknown"

        # Hydroxyurea adjustment
        if not profile.on_hydroxyurea and profile.age > 9:
            hydroxy_adj = "Consider starting hydroxyurea 15mg/kg/day if >3 crises/year or severe disease"
        elif profile.on_hydroxyurea and profile.hemoglobin_f_percent < 15:
            hydroxy_adj = "Increase hydroxyurea by 2.5-5mg/kg to target HbF > 20%"
        elif profile.on_hydroxyurea and profile.wbc_k_u_l < 3.0:
            hydroxy_adj = "Reduce hydroxyurea — leukopenia"

        # Oxygen criteria
        if profile.oxygen_saturation < 92:
            oxygen = True

        # Follow-up
        if crisis == CrisisType.STROKE:
            follow = "Chronic transfusion program to maintain HbS < 30%, MRI/MRA, TCD surveillance"
        elif crisis == CrisisType.ACUTE_CHEST:
            follow = "Pulmonary follow-up, consider chronic transfusion or hydroxyurea escalation"
        else:
            follow = "Hematology follow-up in 1-2 weeks, crisis prevention counseling"

        return SickleCellResult(
            severity=severity,
            exchange_transfusion_indicated=exchange,
            simple_transfusion_indicated=simple,
            transfusion_target_hgb_s_percent=target_hgb_s,
            pain_management=pain_mgmt,
            iv_hydration=iv_hydration,
            oxygen_needed=oxygen,
            antibiotics_needed=antibiotics,
            hydroxyurea_adjustment=hydroxy_adj,
            follow_up=follow
        )

    def tcd_stroke_risk(self, velocity_cm_s: float) -> dict:
        """Transcranial Doppler stroke risk."""
        if velocity_cm_s < 170:
            return {"risk": "Low", "action": "Annual TCD surveillance"}
        elif velocity_cm_s < 200:
            return {"risk": "Conditional", "action": "Repeat TCD in 3 months, consider MRI/MRA"}
        else:
            return {"risk": "High", "action": "Start chronic transfusion to maintain HbS < 30%"}


def run():
    calc = SickleCellCalculator()

    print("=" * 60)
    print("Sickle Cell Crisis Calculator")
    print("=" * 60)

    profile = SickleCellProfile(
        hemoglobin_g_dl=6.5, hemoglobin_s_percent=85, hemoglobin_f_percent=8,
        wbc_k_u_l=15, platelets_k_u_l=180, ldh_u_l=800, bilirubin_mg_dl=4.5,
        creatinine_mg_dl=1.0, crisis_type=CrisisType.ACUTE_CHEST,
        pain_score=8, oxygen_saturation=88, fever_present=True
    )

    result = calc.calculate(profile)
    print(f"\nCrisis: {profile.crisis_type.value}")
    print(f"Severity: {result.severity}")
    print(f"Exchange transfusion: {result.exchange_transfusion_indicated}")
    print(f"Simple transfusion: {result.simple_transfusion_indicated}")
    print(f"Oxygen: {result.oxygen_needed}, Antibiotics: {result.antibiotics_needed}")
    print(f"Pain management: {result.pain_management}")
    print(f"Hydroxyurea: {result.hydroxyurea_adjustment}")

    print(f"\nTCD stroke risk (220 cm/s): {calc.tcd_stroke_risk(220)}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
