"""
Burn Calculator & Parkland Resuscitation — Emergency Medicine
Rule of Nines TBSA estimation, fluid resuscitation, and severity classification.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum


class BurnDepth(Enum):
    FIRST_DEGREE = "first_degree"      # Superficial
    SECOND_DEGREE_PARTIAL = "second_partial"  # Partial thickness
    SECOND_DEGREE_FULL = "second_full"         # Deep partial
    THIRD_DEGREE = "third_degree"      # Full thickness
    FOURTH_DEGREE = "fourth_degree"    # Into fascia/bone


class AgeGroup(Enum):
    ADULT = "adult"
    CHILD = "child"
    INFANT = "infant"


@dataclass
class BodyPartBurn:
    body_part: str
    percent_of_body: float
    depth: BurnDepth
    circumferential: bool = False


@dataclass
class BurnProfile:
    age_group: AgeGroup
    weight_kg: float
    height_cm: float
    burns: List[BodyPartBurn]
    inhalation_injury: bool = False
    electrical_injury: bool = False
    chemical_burn: bool = False
    time_since_injury_hours: float = 0.0
    pre_existing_conditions: List[str] = None

    def __post_init__(self):
        if self.pre_existing_conditions is None:
            self.pre_existing_conditions = []


@dataclass
class BurnResult:
    total_tbsa_percent: float
    tbsa_by_depth: Dict[str, float]
    parkland_total_24h_ml: float
    parkland_first_8h_ml: float
    parkland_next_16h_ml: float
    severity: str
    disposition: str
    burn_center_criteria: List[str]
    monitoring: List[str]
    notes: List[str]


class BurnCalculator:
    """Rule of Nines + Parkland formula burn resuscitation."""

    # Adult Rule of Nines (simplified)
    RULE_OF_NINES: Dict[str, float] = {
        "head": 9, "chest": 9, "abdomen": 9, "back": 18,
        "each_arm": 9, "each_leg": 18, "perineum": 1,
    }

    def calculate(self, profile: BurnProfile) -> BurnResult:
        if profile.weight_kg <= 0:
            raise ValueError("Weight must be > 0 kg")

        total_tbsa = sum(b.percent_of_body for b in profile.burns)
        tbsa_by_depth = {}
        for b in profile.burns:
            key = b.depth.value
            tbsa_by_depth[key] = tbsa_by_depth.get(key, 0) + b.percent_of_body

        # Parkland formula: 4 mL × kg × %TBSA (first 24h)
        # Half in first 8h, half in next 16h from time of injury
        parkland_total = 4 * profile.weight_kg * total_tbsa
        first_8h = parkland_total / 2
        next_16h = parkland_total / 2

        # Adjust for electrical/chemical (may need more)
        if profile.electrical_injury:
            parkland_total *= 1.5
            first_8h = parkland_total / 2
            next_16h = parkland_total / 2

        # Severity classification
        if total_tbsa >= 30 or (profile.inhalation_injury and total_tbsa >= 15):
            severity = "Critical / Major"
            disposition = "Burn center + ICU"
        elif total_tbsa >= 15 or profile.inhalation_injury or profile.electrical_injury:
            severity = "Major"
            disposition = "Burn center referral"
        elif total_tbsa >= 5:
            severity = "Moderate"
            disposition = "Inpatient admission"
        else:
            severity = "Minor"
            disposition = "Outpatient / ED observation"

        # Burn center criteria (ABA guidelines)
        burn_center = []
        if total_tbsa >= 20:
            burn_center.append("Partial-thickness burns > 20% TBSA")
        if any(b.depth in {BurnDepth.THIRD_DEGREE, BurnDepth.FOURTH_DEGREE} for b in profile.burns):
            burn_center.append("Full-thickness burns")
        if any(b.circumferential for b in profile.burns):
            burn_center.append("Circumferential burns (escharotomy risk)")
        if profile.inhalation_injury:
            burn_center.append("Inhalation injury")
        if profile.electrical_injury:
            burn_center.append("Electrical burn")
        if profile.chemical_burn:
            burn_center.append("Chemical burn")
        if profile.age_group in {AgeGroup.INFANT, AgeGroup.CHILD} and total_tbsa >= 10:
            burn_center.append("Pediatric burns > 10% TBSA")
        if any(p in profile.pre_existing_conditions for p in ["diabetes", "immunocompromised"]):
            burn_center.append("Comorbidities compromising healing")

        monitoring = ["Vitals q15-30min", "Urine output (0.5-1 mL/kg/hr)", "Fluid rate titration"]
        if profile.inhalation_injury:
            monitoring += ["ABG", "Carboxyhemoglobin", "Bronchoscopy if indicated"]
        if profile.electrical_injury:
            monitoring += ["ECG", "Troponin", "CK/Myoglobin", "Compartment check"]
        if any(b.circumferential for b in profile.burns):
            monitoring += ["Circumferential site perfusion check", "Escharotomy readiness"]

        notes = []
        if total_tbsa > 0:
            notes.append(f"Total TBSA: {total_tbsa}%")
        for depth, pct in tbsa_by_depth.items():
            notes.append(f"  {depth}: {pct}%")
        if profile.inhalation_injury:
            notes.append("Inhalation injury present — high risk for airway compromise.")
        if parkland_total > 0:
            notes.append(f"Parkland: {parkland_total} mL total (first 8h: {first_8h} mL, next 16h: {next_16h} mL)")
        else:
            notes.append("No fluid resuscitation needed for minor burns.")

        return BurnResult(
            total_tbsa_percent=round(total_tbsa, 1),
            tbsa_by_depth={k: round(v, 1) for k, v in tbsa_by_depth.items()},
            parkland_total_24h_ml=round(parkland_total, 1),
            parkland_first_8h_ml=round(first_8h, 1),
            parkland_next_16h_ml=round(next_16h, 1),
            severity=severity,
            disposition=disposition,
            burn_center_criteria=burn_center,
            monitoring=monitoring,
            notes=notes
        )

    def child_rule_of_nines(self, age_years: int) -> Dict[str, float]:
        """Modified Lund-Browder / pediatric Rule of Nines."""
        head = 19 - age_years  # Approximation
        each_leg = 13.5 + age_years * 0.5
        return {
            "head": head,
            "each_leg": each_leg,
            "each_arm": 9,
            "chest": 9,
            "abdomen": 9,
            "back": 18,
            "perineum": 1,
        }


def run():
    calc = BurnCalculator()

    print("=" * 60)
    print("Burn Calculator & Parkland Resuscitation")
    print("=" * 60)

    burns = [
        BodyPartBurn("chest", 9, BurnDepth.SECOND_DEGREE_PARTIAL),
        BodyPartBurn("abdomen", 9, BurnDepth.SECOND_DEGREE_PARTIAL),
        BodyPartBurn("left_arm", 9, BurnDepth.THIRD_DEGREE, circumferential=True),
    ]

    profile = BurnProfile(
        age_group=AgeGroup.ADULT,
        weight_kg=70,
        height_cm=175,
        burns=burns,
        inhalation_injury=True,
        time_since_injury_hours=1.5
    )

    result = calc.calculate(profile)
    print(f"\nTotal TBSA: {result.total_tbsa_percent}%")
    print(f"Severity: {result.severity}")
    print(f"Disposition: {result.disposition}")
    print(f"Burn center criteria: {result.burn_center_criteria}")
    print(f"Parkland 24h: {result.parkland_total_24h_ml} mL")
    print(f"  First 8h: {result.parkland_first_8h_ml} mL")
    print(f"  Next 16h: {result.parkland_next_16h_ml} mL")
    print(f"Monitoring: {result.monitoring}")
    print(f"Notes: {result.notes}")

    print(f"\nPediatric Rule of Nines (5 years): {calc.child_rule_of_nines(5)}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
