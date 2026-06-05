"""
Chemotherapy Dosing Calculator — Oncology
BSA-based dosing with renal/hepatic adjustment and toxicity risk.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List, Dict
from enum import Enum
import math


class ChemoAgent(Enum):
    CARBOPLATIN = "carboplatin"
    CISPLATIN = "cisplatin"
    DOXORUBICIN = "doxorubicin"
    CYCLOPHOSPHAMIDE = "cyclophosphamide"
    PACLITAXEL = "paclitaxel"
    DOCETAXEL = "docetaxel"
    FIVE_FU = "5_fluorouracil"
    GEMCITABINE = "gemcitabine"
    OXALIPLATIN = "oxaliplatin"
    IRINOTECAN = "irinotecan"
    ETOPOSIDE = "etoposide"
    VINCRISTINE = "vincristine"


@dataclass
class ChemoProfile:
    agent: ChemoAgent
    height_cm: float
    weight_kg: float
    dose_mg_m2: float
    creatinine_clearance_ml_min: float = 100.0
    bilirubin_mg_dl: float = 1.0
    platelets_k_u_l: float = 250.0
    neutrophils_u_l: float = 4000.0
    prior_cycles: int = 0
    prior_toxicity: List[str] = None

    def __post_init__(self):
        if self.prior_toxicity is None:
            self.prior_toxicity = []


@dataclass
class ChemoResult:
    bsa_m2: float
    calculated_dose_mg: float
    adjusted_dose_mg: float
    adjustment_reason: str
    max_lifetime_dose_mg: float
    toxicity_risk: str
    monitoring: List[str]
    pre_medications: List[str]
    cycle_interval_days: int
    notes: List[str]


class ChemoDosingCalculator:
    """Chemotherapy BSA dosing with organ function adjustments."""

    # Calvert formula for carboplatin: AUC x (GFR + 25)
    # Doxorubicin lifetime max ~ 550 mg/m2 (450 if prior RT)
    MAX_LIFETIME: Dict[ChemoAgent, float] = {
        ChemoAgent.DOXORUBICIN: 550.0,
        ChemoAgent.CISPLATIN: float("inf"),
        ChemoAgent.CARBOPLATIN: float("inf"),
    }

    def calculate(self, profile: ChemoProfile) -> ChemoResult:
        # BSA (Du Bois)
        bsa = 0.007184 * (profile.height_cm ** 0.725) * (profile.weight_kg ** 0.425)
        base_dose = profile.dose_mg_m2 * bsa

        adjusted = base_dose
        reason = "No adjustment needed"
        notes = []

        # Organ-specific adjustments
        if profile.agent == ChemoAgent.CARBOPLATIN:
            # Calvert formula: AUC x (CrCl + 25)
            # Assume AUC = 5 if dose_mg_m2 is used as AUC target
            auc_target = profile.dose_mg_m2  # Treat dose as AUC target for carboplatin
            adjusted = auc_target * (profile.creatinine_clearance_ml_min + 25)
            reason = f"Calvert formula: AUC {auc_target} x (CrCl {profile.creatinine_clearance_ml_min} + 25)"
        elif profile.agent == ChemoAgent.CISPLATIN:
            if profile.creatinine_clearance_ml_min < 60:
                adjusted = base_dose * 0.75
                reason = "Cisplatin reduced 25% for CrCl < 60"
            elif profile.creatinine_clearance_ml_min < 45:
                adjusted = base_dose * 0.5
                reason = "Cisplatin reduced 50% for CrCl < 45"
            notes.append("Aggressive hydration + magnesium supplementation required")
        elif profile.agent == ChemoAgent.DOXORUBICIN:
            if profile.bilirubin_mg_dl > 2:
                adjusted = base_dose * 0.5
                reason = "Doxorubicin reduced 50% for bilirubin > 2"
            elif profile.bilirubin_mg_dl > 1.5:
                adjusted = base_dose * 0.75
                reason = "Doxorubicin reduced 25% for bilirubin 1.5-2"
        elif profile.agent in [ChemoAgent.DOCETAXEL, ChemoAgent.PACLITAXEL]:
            if profile.bilirubin_mg_dl > 2:
                adjusted = base_dose * 0.5
                reason = "Taxane reduced 50% for elevated bilirubin"
            notes.append("Premedicate with dexamethasone (taxane)")
        elif profile.agent == ChemoAgent.IRINOTECAN:
            if profile.bilirubin_mg_dl > 2:
                adjusted = base_dose * 0.75
                reason = "Irinotecan reduced 25% for bilirubin > 2"
            notes.append("UGT1A1 testing recommended if available (dose adjustment for *28/*28)")

        # Hematologic toxicity check
        if profile.platelets_k_u_l < 100:
            notes.append("Thrombocytopenia — consider dose delay or reduction")
        if profile.neutrophils_u_l < 1500:
            notes.append("Neutropenia — G-CSF prophylaxis or dose delay")

        # Toxicity risk
        toxic_score = 0
        if profile.age > 65:
            toxic_score += 2
        if profile.creatinine_clearance_ml_min < 60:
            toxic_score += 2
        if profile.bilirubin_mg_dl > 1.5:
            toxic_score += 2
        if profile.prior_toxicity:
            toxic_score += 2
        if profile.prior_cycles > 4:
            toxic_score += 1

        if toxic_score >= 6:
            tox_risk = "High"
        elif toxic_score >= 3:
            tox_risk = "Moderate"
        else:
            tox_risk = "Standard"

        max_lifetime = self.MAX_LIFETIME.get(profile.agent, float("inf"))
        if max_lifetime != float("inf"):
            max_lifetime *= bsa

        premeds = ["Antiemetic (ondansetron + dexamethasone)", "IV hydration"]
        if profile.agent in [ChemoAgent.PACLITAXEL, ChemoAgent.DOCETAXEL]:
            premeds += ["Dexamethasone 20mg PO/IV x 3 doses", "H1/H2 blockers (diphenhydramine + cimetidine)"]
        if profile.agent == ChemoAgent.CISPLATIN:
            premeds += ["Mannitol or furosemide diuresis", "Magnesium supplementation"]

        monitoring = ["CBC before each cycle", "CMP (renal, hepatic function)", "Tumor markers if applicable"]
        if profile.agent == ChemoAgent.DOXORUBICIN:
            monitoring.append("Echocardiogram before cycle 1, then every 2-3 cycles")
        if profile.agent == ChemoAgent.CISPLATIN:
            monitoring.append("Audiology (ototoxicity), Mg, K+ monitoring")

        cycle_interval = 21  # Standard
        if profile.agent == ChemoAgent.GEMCITABINE:
            cycle_interval = 28
        elif profile.agent == ChemoAgent.DOCETAXEL:
            cycle_interval = 21

        return ChemoResult(
            bsa_m2=round(bsa, 2),
            calculated_dose_mg=round(base_dose, 1),
            adjusted_dose_mg=round(adjusted, 1),
            adjustment_reason=reason,
            max_lifetime_dose_mg=round(max_lifetime, 1) if max_lifetime != float("inf") else 0,
            toxicity_risk=tox_risk,
            monitoring=monitoring,
            pre_medications=premeds,
            cycle_interval_days=cycle_interval,
            notes=notes
        )


def run():
    calc = ChemoDosingCalculator()

    print("=" * 60)
    print("Chemotherapy Dosing Calculator")
    print("=" * 60)

    profile = ChemoProfile(
        agent=ChemoAgent.CARBOPLATIN, height_cm=170, weight_kg=70,
        dose_mg_m2=5.0,  # AUC 5 for carboplatin
        creatinine_clearance_ml_min=55, bilirubin_mg_dl=1.2,
        platelets_k_u_l=180, neutrophils_u_l=2200
    )

    result = calc.calculate(profile)
    print(f"\nBSA: {result.bsa_m2} m²")
    print(f"Base dose: {result.calculated_dose_mg} mg")
    print(f"Adjusted dose: {result.adjusted_dose_mg} mg ({result.adjustment_reason})")
    print(f"Toxicity risk: {result.toxicity_risk}")
    print(f"Premedications: {result.pre_medications}")
    print(f"Monitoring: {result.monitoring}")
    print(f"Notes: {result.notes}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
