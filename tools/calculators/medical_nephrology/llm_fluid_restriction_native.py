"""
Fluid Restriction Calculator — Nephrology
Daily fluid limits for heart failure, CKD, and dialysis patients.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class FluidProfile:
    weight_kg: float
    diagnosis: str  # "ckd", "dialysis", "heart_failure", "hyponatremia"
    egfr: float = 0.0
    urine_output_ml_day: float = 0.0
    dialytic_weight_gain_kg: float = 0.0
    serum_sodium_mmol_l: float = 140.0
    edema_present: bool = False
    pulmonary_congestion: bool = False
    hf_nyha_class: int = 0  # 1-4
    temperature_celsius: float = 37.0
    activity_level: str = "sedentary"  # sedentary, light, moderate


@dataclass
class FluidResult:
    daily_fluid_limit_ml: int
    fluid_from_food_ml: int
    free_water_limit_ml: int
    sodium_restriction_mg: int
    rationale: str
    monitoring: List[str]
    warnings: List[str]


class FluidRestrictionCalculator:
    """Daily fluid restriction for renal and cardiac patients."""

    def calculate(self, profile: FluidProfile) -> FluidResult:
        # Base fluid need ~ 30-35 mL/kg
        base = profile.weight_kg * 30

        if profile.diagnosis == "dialysis":
            # Interdialytic weight gain < 1kg/day
            # Fluid limit = urine output + 500mL (insensible losses)
            limit = profile.urine_output_ml_day + 500
            if profile.dialytic_weight_gain_kg > 1.5:
                limit = max(500, limit - 500)  # Stricter
            sodium = 2000
            rationale = "Dialysis: insensible losses (500mL) + urine output. IDWG < 1kg/day target."
            warnings = ["Fluid includes ice, soups, gelatin, coffee, tea, medications"] if limit < 1000 else []

        elif profile.diagnosis == "heart_failure":
            if profile.hf_nyha_class >= 3:
                limit = 1500
            elif profile.hf_nyha_class == 2:
                limit = 2000
            else:
                limit = 2500
            if profile.pulmonary_congestion:
                limit = 1200
            sodium = 2000
            rationale = f"Heart failure NYHA class {profile.hf_nyha_class}: fluid restriction to reduce preload."
            warnings = ["Monitor daily weight — gain >1kg/day = fluid retention"]

        elif profile.diagnosis == "hyponatremia":
            # Free water restriction for SIADH/euvolemic hyponatremia
            if profile.serum_sodium_mmol_l < 125:
                limit = 800
            elif profile.serum_sodium_mmol_l < 130:
                limit = 1200
            else:
                limit = 1500
            sodium = 2000
            rationale = f"Hyponatremia (Na {profile.serum_sodium_mmol_l}): restrict free water to raise sodium."
            warnings = ["Correct sodium slowly (< 8-10 mmol/L in 24h) to avoid osmotic demyelination"]

        else:  # CKD
            if profile.egfr < 15:
                limit = 1500
            elif profile.egfr < 30:
                limit = 2000
            elif profile.egfr < 60:
                limit = 2500
            else:
                limit = base
            sodium = 2000
            rationale = f"CKD stage (eGFR {profile.egfr}): fluid restriction to prevent volume overload."
            warnings = []

        if profile.edema_present:
            limit = int(limit * 0.8)
            warnings.append("Edema present — further fluid restriction applied")

        # Food contributes ~500-700mL water
        food_fluid = 600
        free_water = max(0, limit - food_fluid)

        monitoring = ["Daily weight at same time", "Blood pressure", "Edema assessment", "I/O charting"]
        if profile.diagnosis == "dialysis":
            monitoring.append("Pre/post dialysis weight (IDWG)")
        if profile.diagnosis == "heart_failure":
            monitoring.append("BNP/NT-proBNP trend")
        if profile.diagnosis == "hyponatremia":
            monitoring.append("Sodium checks every 6-12 hours initially")

        return FluidResult(
            daily_fluid_limit_ml=limit,
            fluid_from_food_ml=food_fluid,
            free_water_limit_ml=free_water,
            sodium_restriction_mg=sodium,
            rationale=rationale,
            monitoring=monitoring,
            warnings=warnings
        )


def run():
    calc = FluidRestrictionCalculator()

    print("=" * 60)
    print("Fluid Restriction Calculator")
    print("=" * 60)

    cases = [
        FluidProfile(70, "dialysis", urine_output_ml_day=200, dialytic_weight_gain_kg=2.5),
        FluidProfile(80, "heart_failure", hf_nyha_class=3, pulmonary_congestion=True, edema_present=True),
        FluidProfile(65, "hyponatremia", serum_sodium_mmol_l=122),
    ]

    for i, c in enumerate(cases, 1):
        result = calc.calculate(c)
        print(f"\nCase {i}: {c.diagnosis}")
        print(f"  Fluid limit: {result.daily_fluid_limit_ml} mL/day")
        print(f"  Free water: {result.free_water_limit_ml} mL/day")
        print(f"  Sodium: {result.sodium_restriction_mg} mg/day")
        print(f"  Rationale: {result.rationale}")
        print(f"  Warnings: {result.warnings}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
