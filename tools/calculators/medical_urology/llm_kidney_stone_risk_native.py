"""
Kidney Stone Risk Calculator — Urology
Urinary stone composition risk, 24-hour urine analysis, and prevention.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class StoneType(Enum):
    CALCIUM_OXALATE = "calcium_oxalate"
    CALCIUM_PHOSPHATE = "calcium_phosphate"
    URIC_ACID = "uric_acid"
    STRUVITE = "struvite"
    CYSTINE = "cystine"


@dataclass
class StoneRiskProfile:
    age: int
    gender: str
    bmi: float
    prior_stones: int
    family_history: bool
    urine_volume_l_day: float
    urine_calcium_mg_day: float
    urine_oxalate_mg_day: float
    urine_uric_acid_mg_day: float
    urine_citrate_mg_day: float
    urine_ph: float
    urine_sodium_mmol_day: float
    serum_uric_acid_mg_dl: float
    diabetes: bool = False
    gout: bool = False
    bowel_disease: bool = False
    recurrent_utis: bool = False


@dataclass
class StoneRiskResult:
    stone_types_at_risk: List[StoneType]
    risk_scores: dict
    supersaturation_estimate: str
    dietary_recommendations: List[str]
    pharmacological_recommendations: List[str]
    follow_up_24h_urine: str
    imaging_follow_up: str


class KidneyStoneCalculator:
    """24-hour urine stone risk assessment."""

    def calculate(self, profile: StoneRiskProfile) -> StoneRiskResult:
        risks = {}
        stone_types = []
        recs = []
        pharma = []

        # Calcium oxalate risk
        ca_ox_score = 0
        if profile.urine_calcium_mg_day > 250:
            ca_ox_score += 3
        if profile.urine_oxalate_mg_day > 40:
            ca_ox_score += 3
        if profile.urine_volume_l_day < 2:
            ca_ox_score += 2
        if profile.urine_citrate_mg_day < 320:
            ca_ox_score += 2
        if profile.bmi > 30:
            ca_ox_score += 1
        risks["calcium_oxalate"] = ca_ox_score
        if ca_ox_score >= 5:
            stone_types.append(StoneType.CALCIUM_OXALATE)

        # Uric acid risk
        ua_score = 0
        if profile.urine_ph < 5.5:
            ua_score += 3
        if profile.urine_uric_acid_mg_day > 800:
            ua_score += 2
        if profile.serum_uric_acid_mg_dl > 7:
            ua_score += 2
        if profile.gout:
            ua_score += 2
        if profile.diabetes:
            ua_score += 1
        risks["uric_acid"] = ua_score
        if ua_score >= 4:
            stone_types.append(StoneType.URIC_ACID)

        # Calcium phosphate risk
        ca_phos_score = 0
        if profile.urine_ph > 6.5:
            ca_phos_score += 3
        if profile.urine_calcium_mg_day > 250:
            ca_phos_score += 2
        risks["calcium_phosphate"] = ca_phos_score
        if ca_phos_score >= 4:
            stone_types.append(StoneType.CALCIUM_PHOSPHATE)

        # Struvite (infection stones)
        if profile.recurrent_utis:
            stone_types.append(StoneType.STRUVITE)
            risks["struvite"] = 5
        else:
            risks["struvite"] = 0

        # Cystine (genetic, rare)
        if profile.urine_oxalate_mg_day > 100 and profile.family_history:
            # This is a weak proxy — actual cystine requires specific test
            risks["cystine"] = 1
        else:
            risks["cystine"] = 0

        # Supersaturation
        if ca_ox_score >= 6 or ua_score >= 5:
            ss = "High supersaturation risk"
        elif ca_ox_score >= 4 or ua_score >= 3:
            ss = "Moderate supersaturation risk"
        else:
            ss = "Low supersaturation risk"

        # Dietary recommendations
        recs = ["Fluid intake: 2.5-3.0 L/day (urine output > 2L/day)", "Limit sodium < 2g/day"]
        if StoneType.CALCIUM_OXALATE in stone_types:
            recs += ["Moderate calcium intake (800-1000mg/day) — do NOT restrict", "Limit oxalate-rich foods (spinach, nuts, rhubarb, beets)", "Increase citrate (lemon/lime juice)"]
        if StoneType.URIC_ACID in stone_types:
            recs += ["Alkalinize urine (potassium citrate target pH 6.5)", "Limit purine-rich foods (red meat, organ meats, shellfish)", "Limit alcohol (especially beer)", "Reduce fructose intake"]
        if StoneType.CALCIUM_PHOSPHATE in stone_types:
            recs += ["Monitor urine pH — avoid over-alkalinization", "Thiazide diuretics if hypercalciuria"]
        if StoneType.STRUVITE in stone_types:
            recs += ["Complete stone removal + treat infection", "Long-term antibiotic suppression if needed"]
        if profile.bmi > 30:
            recs.append("Weight reduction — obesity is a stone risk factor")
        if profile.bowel_disease:
            recs.append("Bowel disease — check for enteric hyperoxaluria, ensure adequate hydration")

        # Pharmacological
        if profile.urine_calcium_mg_day > 250:
            pharma.append("Thiazide diuretics (HCTZ 25mg daily) for hypercalciuria")
        if profile.urine_citrate_mg_day < 320:
            pharma.append("Potassium citrate (Urocit-K) for hypocitraturia")
        if profile.urine_uric_acid_mg_day > 800 or profile.gout:
            pharma.append("Allopurinol 300mg daily if hyperuricosuria or gout")
        if profile.urine_ph < 5.5 and StoneType.URIC_ACID in stone_types:
            pharma.append("Potassium citrate to alkalinize urine to pH 6.0-6.5")

        return StoneRiskResult(
            stone_types_at_risk=stone_types,
            risk_scores=risks,
            supersaturation_estimate=ss,
            dietary_recommendations=recs,
            pharmacological_recommendations=pharma,
            follow_up_24h_urine="Repeat 24h urine 6-8 weeks after dietary/pharmacological intervention",
            imaging_follow_up="KUB/CT if symptomatic; annual ultrasound if recurrent stone former"
        )

    def stone_composition_probability(self, ct_hounsfield_units: float, urine_ph: float) -> dict:
        """Estimate stone composition from CT density."""
        if ct_hounsfield_units > 1000:
            return {"composition": "Calcium oxalate likely", "confidence": "High"}
        elif ct_hounsfield_units > 400:
            return {"composition": "Calcium phosphate or calcium oxalate", "confidence": "Moderate"}
        elif ct_hounsfield_units < 200 and urine_ph < 5.5:
            return {"composition": "Uric acid likely", "confidence": "High"}
        elif ct_hounsfield_units < 400 and urine_ph > 7.0:
            return {"composition": "Struvite or calcium phosphate", "confidence": "Moderate"}
        else:
            return {"composition": "Mixed or indeterminate", "confidence": "Low"}


def run():
    calc = KidneyStoneCalculator()

    print("=" * 60)
    print("Kidney Stone Risk Calculator")
    print("=" * 60)

    profile = StoneRiskProfile(
        age=45, gender="male", bmi=32, prior_stones=2, family_history=True,
        urine_volume_l_day=1.2, urine_calcium_mg_day=320, urine_oxalate_mg_day=55,
        urine_uric_acid_mg_day=900, urine_citrate_mg_day=180, urine_ph=5.2,
        urine_sodium_mmol_day=220, serum_uric_acid_mg_dl=8.5, gout=True, diabetes=True
    )

    result = calc.calculate(profile)
    print(f"\nStone types at risk: {[s.value for s in result.stone_types_at_risk]}")
    print(f"Risk scores: {result.risk_scores}")
    print(f"Supersaturation: {result.supersaturation_estimate}")
    print(f"Dietary: {result.dietary_recommendations}")
    print(f"Pharmacological: {result.pharmacological_recommendations}")

    print(f"\nStone composition (CT 1200 HU, pH 5.2): {calc.stone_composition_probability(1200, 5.2)}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
