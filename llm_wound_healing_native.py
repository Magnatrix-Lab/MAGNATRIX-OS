"""
Wound Healing Calculator — Dermatology
Wound assessment, healing trajectory, and dressing selection.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum
import math


class WoundType(Enum):
    PRESSURE = "pressure"
    VENOUS = "venous"
    ARTERIAL = "arterial"
    DIABETIC = "diabetic"
    TRAUMATIC = "traumatic"
    SURGICAL = "surgical"
    BURN = "burn"
    MIXED = "mixed"


class WoundStage(Enum):
    STAGE_1 = "stage_1"  # Intact skin erythema
    STAGE_2 = "stage_2"  # Partial thickness
    STAGE_3 = "stage_3"  # Full thickness, no fascia
    STAGE_4 = "stage_4"  # Full thickness, exposed bone/tendon/muscle
    UNSTAGEABLE = "unstageable"
    DEEP_TISSUE = "deep_tissue_injury"


@dataclass
class WoundProfile:
    wound_type: WoundType
    stage: WoundStage
    area_cm2: float
    depth_mm: float
    undermining: bool = False
    tunneling: bool = False
    exudate_level: str = "moderate"  # none, minimal, moderate, heavy
    infection_signs: List[str] = None
    tissue_type: str = "granulation"  # necrotic, slough, granulation, epithelial
    patient_age: int = 60
    diabetes: bool = False
    smoker: bool = False
    malnutrition: bool = False
    mobility: str = "limited"  # bedbound, limited, ambulatory
    weeks_open: int = 0
    previous_area_cm2: Optional[float] = None
    weeks_since_previous: int = 1

    def __post_init__(self):
        if self.infection_signs is None:
            self.infection_signs = []


@dataclass
class WoundResult:
    healing_probability: float
    estimated_weeks_to_heal: int
    healing_rate_cm2_per_week: float
    dressing_recommendations: List[str]
    debridement_needed: bool
    offloading_needed: bool
    compression_needed: bool
    antibiotics_needed: bool
    notes: List[str]


class WoundHealingCalculator:
    """Wound healing assessment and management guidance."""

    def calculate(self, profile: WoundProfile) -> WoundResult:
        notes = []

        # Base healing estimate by type and stage
        base_weeks = {
            WoundStage.STAGE_1: 1, WoundStage.STAGE_2: 2,
            WoundStage.STAGE_3: 4, WoundStage.STAGE_4: 8,
            WoundStage.UNSTAGEABLE: 6, WoundStage.DEEP_TISSUE: 3
        }.get(profile.stage, 4)

        # Size factor: larger wounds take longer
        size_factor = max(1, profile.area_cm2 / 10)

        # Modifiers
        modifiers = 1.0
        if profile.diabetes:
            modifiers *= 1.5
            notes.append("Diabetes impairs healing — tight glucose control needed.")
        if profile.smoker:
            modifiers *= 1.4
            notes.append("Smoking significantly impairs wound healing.")
        if profile.malnutrition:
            modifiers *= 1.5
            notes.append("Malnutrition — albumin/pre-albumin assessment, protein supplementation.")
        if profile.mobility == "bedbound":
            modifiers *= 1.3
            notes.append("Immobility increases pressure injury risk.")
        if profile.wound_type == WoundType.ARTERIAL:
            modifiers *= 2.0
            notes.append("Arterial insufficiency — vascular consult required.")
        if profile.wound_type == WoundType.VENOUS:
            notes.append("Venous insufficiency — compression therapy is key.")

        # Infection
        antibiotics = len(profile.infection_signs) >= 2
        if antibiotics:
            modifiers *= 1.5
            notes.append(f"Infection signs: {profile.infection_signs} — culture and antibiotics.")

        # Debridement
        debride = profile.tissue_type in ["necrotic", "slough"]
        if debride:
            notes.append("Debridement needed to remove non-viable tissue.")

        estimated_weeks = int(base_weeks * size_factor * modifiers)
        estimated_weeks = max(1, estimated_weeks)

        # Healing rate
        if profile.previous_area_cm2 and profile.weeks_since_previous > 0:
            rate = (profile.previous_area_cm2 - profile.area_cm2) / profile.weeks_since_previous
        else:
            rate = profile.area_cm2 / estimated_weeks if estimated_weeks > 0 else 0

        # Probability (rough heuristic)
        prob = max(0.1, 0.9 - (modifiers - 1.0) * 0.3 - profile.weeks_open * 0.01)

        # Dressing
        dressings = []
        if profile.exudate_level == "none":
            dressings.append("Hydrogel or moisture-retentive dressing")
        elif profile.exudate_level == "minimal":
            dressings.append("Hydrocolloid or thin foam")
        elif profile.exudate_level == "moderate":
            dressings.append("Foam dressing")
        else:
            dressings.append("Alginate or super-absorbent foam")

        if debride:
            dressings.append("Hydrogel or enzymatic debriding agent")
        if profile.infection_signs:
            dressings.append("Antimicrobial dressing (silver/iodine)")
        if profile.tissue_type == "granulation":
            dressings.append("Maintain moist environment — collagen or foam")

        offloading = profile.wound_type == WoundType.PRESSURE or profile.mobility == "bedbound"
        compression = profile.wound_type == WoundType.VENOUS and not profile.arterial_component()

        return WoundResult(
            healing_probability=round(prob, 3),
            estimated_weeks_to_heal=estimated_weeks,
            healing_rate_cm2_per_week=round(rate, 2),
            dressing_recommendations=dressings,
            debridement_needed=debride,
            offloading_needed=offloading,
            compression_needed=compression,
            antibiotics_needed=antibiotics,
            notes=notes
        )

    def arterial_component(self, profile):
        """Check if arterial component suspected."""
        return profile.wound_type == WoundType.ARTERIAL or profile.wound_type == WoundType.MIXED


WoundProfile.arterial_component = lambda self: WoundHealingCalculator.arterial_component(None, self)


def run():
    calc = WoundHealingCalculator()

    print("=" * 60)
    print("Wound Healing Calculator")
    print("=" * 60)

    profile = WoundProfile(
        wound_type=WoundType.DIABETIC,
        stage=WoundStage.STAGE_3,
        area_cm2=4.5,
        depth_mm=8,
        exudate_level="moderate",
        tissue_type="slough",
        diabetes=True,
        smoker=False,
        weeks_open=3
    )

    result = calc.calculate(profile)
    print(f"\nHealing probability: {result.healing_probability}")
    print(f"Est. weeks to heal: {result.estimated_weeks_to_heal}")
    print(f"Healing rate: {result.healing_rate_cm2_per_week} cm²/week")
    print(f"Dressings: {result.dressing_recommendations}")
    print(f"Debridement: {result.debridement_needed}")
    print(f"Offloading: {result.offloading_needed}")
    print(f"Antibiotics: {result.antibiotics_needed}")
    print(f"Notes: {result.notes}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
