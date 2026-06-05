"""
Poisoning & Toxicology Calculator — Emergency Medicine
Toxicology dose estimation, risk stratification, and antidote reference.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import math


class PoisonType(Enum):
    ACETAMINOPHEN = "acetaminophen"
    IBUPROFEN = "ibuprofen"
    ASPIRIN = "aspirin"
    ETHANOL = "ethanol"
    METHANOL = "methanol"
    ETHYLENE_GLYCOL = "ethylene_glycol"
    OPIOID = "opioid"
    BENZODIAZEPINE = "benzodiazepine"
    TCA = "tricyclic_antidepressant"
    BETA_BLOCKER = "beta_blocker"
    CALCIUM_CHANNEL_BLOCKER = "ccb"
    IRON = "iron"
    LITHIUM = "lithium"
    CARBON_MONOXIDE = "carbon_monoxide"
    CYANIDE = "cyanide"
    ORGANOPHOSPHATE = "organophosphate"
    HEAVY_METAL = "heavy_metal"
    UNKNOWN = "unknown"


class ToxicityLevel(Enum):
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    LIFE_THREATENING = "life_threatening"


@dataclass
class PoisoningProfile:
    poison_type: PoisonType
    ingested_dose_mg: float = 0.0
    ingested_dose_ml: float = 0.0
    weight_kg: float = 70.0
    time_since_exposure_hours: float = 0.0
    serum_level: Optional[float] = None
    co_ingestions: List[PoisonType] = field(default_factory=list)
    symptoms: List[str] = field(default_factory=list)


@dataclass
class PoisoningResult:
    mg_per_kg: float
    toxicity_level: ToxicityLevel
    antidote: Optional[str]
    activated_charcoal_indicated: bool
    hemodialysis_indicated: bool
    lab_monitoring: List[str]
    disposition: str
    notes: List[str]


class PoisoningCalculator:
    """Toxicology dose estimation and clinical management guidance."""

    TOXIC_DOSE: Dict[PoisonType, Dict[str, float]] = {
        PoisonType.ACETAMINOPHEN: {"mild": 50, "moderate": 150, "severe": 300, "lethal_estimate": 500},
        PoisonType.IBUPROFEN: {"mild": 50, "moderate": 200, "severe": 400, "lethal_estimate": 800},
        PoisonType.ASPIRIN: {"mild": 50, "moderate": 150, "severe": 300, "lethal_estimate": 500},
        PoisonType.ETHANOL: {"mild": 1, "moderate": 3, "severe": 5, "lethal_estimate": 8},
        PoisonType.METHANOL: {"mild": 0.5, "moderate": 2, "severe": 4, "lethal_estimate": 8},
        PoisonType.ETHYLENE_GLYCOL: {"mild": 0.5, "moderate": 2, "severe": 4, "lethal_estimate": 8},
        PoisonType.OPIOID: {"mild": 0.01, "moderate": 0.05, "severe": 0.1, "lethal_estimate": 0.3},
        PoisonType.BENZODIAZEPINE: {"mild": 0.1, "moderate": 0.5, "severe": 1, "lethal_estimate": 3},
        PoisonType.TCA: {"mild": 5, "moderate": 15, "severe": 30, "lethal_estimate": 50},
        PoisonType.BETA_BLOCKER: {"mild": 0.5, "moderate": 2, "severe": 5, "lethal_estimate": 10},
        PoisonType.CALCIUM_CHANNEL_BLOCKER: {"mild": 0.5, "moderate": 2, "severe": 5, "lethal_estimate": 10},
        PoisonType.IRON: {"mild": 20, "moderate": 60, "severe": 100, "lethal_estimate": 200},
        PoisonType.LITHIUM: {"mild": 1, "moderate": 2, "severe": 4, "lethal_estimate": 8},
        PoisonType.CARBON_MONOXIDE: {"mild": 10, "moderate": 25, "severe": 50, "lethal_estimate": 80},
        PoisonType.CYANIDE: {"mild": 0.5, "moderate": 1, "severe": 3, "lethal_estimate": 5},
        PoisonType.ORGANOPHOSPHATE: {"mild": 0.5, "moderate": 2, "severe": 5, "lethal_estimate": 10},
        PoisonType.HEAVY_METAL: {"mild": 1, "moderate": 5, "severe": 10, "lethal_estimate": 20},
    }

    ANTIDOTES: Dict[PoisonType, Optional[str]] = {
        PoisonType.ACETAMINOPHEN: "N-acetylcysteine (NAC)",
        PoisonType.IBUPROFEN: None,
        PoisonType.ASPIRIN: "Sodium bicarbonate (alkalinize urine), dialysis",
        PoisonType.ETHANOL: "Supportive care; thiamine if malnourished",
        PoisonType.METHANOL: "Fomepizole or ethanol + folate",
        PoisonType.ETHYLENE_GLYCOL: "Fomepizole or ethanol + thiamine/pyridoxine",
        PoisonType.OPIOID: "Naloxone",
        PoisonType.BENZODIAZEPINE: "Flumazenil (caution: seizures if chronic use)",
        PoisonType.TCA: "Sodium bicarbonate (QRS widening)",
        PoisonType.BETA_BLOCKER: "Glucagon, high-dose insulin, lipid emulsion",
        PoisonType.CALCIUM_CHANNEL_BLOCKER: "Calcium chloride, high-dose insulin, lipid emulsion",
        PoisonType.IRON: "Deferoxamine",
        PoisonType.LITHIUM: "Hemodialysis if severe",
        PoisonType.CARBON_MONOXIDE: "100% O2; hyperbaric if severe/pregnant",
        PoisonType.CYANIDE: "Hydroxocobalamin or cyanide antidote kit",
        PoisonType.ORGANOPHOSPHATE: "Atropine + pralidoxime (2-PAM)",
        PoisonType.HEAVY_METAL: "Chelation (dimercaprol, EDTA, succimer)",
        PoisonType.UNKNOWN: None,
    }

    def calculate(self, profile: PoisoningProfile) -> PoisoningResult:
        if profile.weight_kg <= 0:
            raise ValueError("Weight must be > 0 kg")

        thresholds = self.TOXIC_DOSE.get(profile.poison_type, {})

        if profile.poison_type == PoisonType.ETHANOL:
            grams = profile.ingested_dose_ml * 0.789
            mg_per_kg = grams * 1000 / profile.weight_kg
        elif profile.poison_type in (PoisonType.METHANOL, PoisonType.ETHYLENE_GLYCOL):
            density = 0.79
            mg_per_kg = profile.ingested_dose_ml * density * 1000 / profile.weight_kg
        else:
            mg_per_kg = profile.ingested_dose_mg / profile.weight_kg

        if not thresholds:
            toxicity = ToxicityLevel.UNKNOWN
        elif mg_per_kg >= thresholds.get("severe", float("inf")):
            toxicity = ToxicityLevel.LIFE_THREATENING if mg_per_kg >= thresholds.get("lethal_estimate", float("inf")) * 0.8 else ToxicityLevel.SEVERE
        elif mg_per_kg >= thresholds.get("moderate", float("inf")):
            toxicity = ToxicityLevel.SEVERE
        elif mg_per_kg >= thresholds.get("mild", float("inf")):
            toxicity = ToxicityLevel.MODERATE
        else:
            toxicity = ToxicityLevel.MILD if mg_per_kg > 0 else ToxicityLevel.NONE

        if profile.serum_level is not None and profile.poison_type == PoisonType.LITHIUM:
            level = profile.serum_level
            if level >= 4.0:
                toxicity = ToxicityLevel.LIFE_THREATENING
            elif level >= 2.5:
                toxicity = ToxicityLevel.SEVERE
            elif level >= 1.5:
                toxicity = ToxicityLevel.MODERATE
            elif level >= 1.0:
                toxicity = ToxicityLevel.MILD

        antidote = self.ANTIDOTES.get(profile.poison_type)

        charcoal_ok = profile.time_since_exposure_hours <= 2 and profile.poison_type not in {
            PoisonType.CARBON_MONOXIDE, PoisonType.CYANIDE, PoisonType.ORGANOPHOSPHATE
        }
        if profile.poison_type in {PoisonType.LITHIUM, PoisonType.IRON, PoisonType.ETHANOL, PoisonType.METHANOL, PoisonType.ETHYLENE_GLYCOL}:
            charcoal_ok = False

        dialysis = False
        if profile.poison_type in {PoisonType.METHANOL, PoisonType.ETHYLENE_GLYCOL} and mg_per_kg >= thresholds.get("moderate", 0):
            dialysis = True
        elif profile.poison_type == PoisonType.LITHIUM and profile.serum_level and profile.serum_level >= 4.0:
            dialysis = True
        elif profile.poison_type == PoisonType.ASPIRIN and mg_per_kg >= 300:
            dialysis = True

        labs = ["CMP (electrolytes, BUN, creatinine)", "LFTs", "ABG/VBG", "CBC"]
        if profile.poison_type == PoisonType.ACETAMINOPHEN:
            labs += ["Acetaminophen level (Rumack-Matthew nomogram)", "INR/PT"]
        elif profile.poison_type == PoisonType.ASPIRIN:
            labs += ["Salicylate level", "ABG (respiratory alkalosis -> metabolic acidosis)"]
        elif profile.poison_type in {PoisonType.METHANOL, PoisonType.ETHYLENE_GLYCOL}:
            labs += ["Serum osmolality", "Osmolar gap", "Anion gap"]
        elif profile.poison_type == PoisonType.CARBON_MONOXIDE:
            labs += ["Carboxyhemoglobin level", "CO level (exhaled)"]
        elif profile.poison_type == PoisonType.LITHIUM:
            labs += ["Lithium level", "TSH"]
        elif profile.poison_type == PoisonType.OPIOID:
            labs += ["Drug screen (expanded)"]
        elif profile.poison_type == PoisonType.ORGANOPHOSPHATE:
            labs += ["RBC cholinesterase activity"]

        if toxicity in {ToxicityLevel.SEVERE, ToxicityLevel.LIFE_THREATENING}:
            disposition = "ICU admission + toxicology consultation"
        elif toxicity == ToxicityLevel.MODERATE:
            disposition = "Inpatient admission (telemetry)"
        elif toxicity == ToxicityLevel.MILD:
            disposition = "ED observation (4-6 hours)"
        else:
            disposition = "Home if asymptomatic with return precautions"

        notes = []
        if profile.co_ingestions:
            notes.append(f"Co-ingestions: {[p.value for p in profile.co_ingestions]}")
        if profile.time_since_exposure_hours > 4:
            notes.append("Late presentation — antidotes may be less effective.")
        if profile.time_since_exposure_hours <= 1 and charcoal_ok:
            notes.append("Consider single-dose activated charcoal if airway protected.")
        if dialysis:
            notes.append("Hemodialysis consultation recommended.")
        if profile.serum_level is not None:
            notes.append(f"Serum level: {profile.serum_level}")

        return PoisoningResult(
            mg_per_kg=round(mg_per_kg, 2),
            toxicity_level=toxicity,
            antidote=antidote,
            activated_charcoal_indicated=charcoal_ok,
            hemodialysis_indicated=dialysis,
            lab_monitoring=labs,
            disposition=disposition,
            notes=notes
        )

    def acetaminophen_rumack_nomogram(self, hours_post_ingestion: float, apap_level_mcg_ml: float) -> Dict:
        treatment_line = 150 * (4 / hours_post_ingestion) ** 1.5 if hours_post_ingestion > 0 else 9999
        risk = apap_level_mcg_ml > treatment_line
        return {
            "hours_post_ingestion": hours_post_ingestion,
            "apap_level_mcg_ml": apap_level_mcg_ml,
            "treatment_line_mcg_ml": round(treatment_line, 2),
            "above_treatment_line": risk,
            "n_acetylcysteine_indicated": risk and hours_post_ingestion <= 24,
            "n_acetylcysteine_dose_g": 140 if risk else 0,
        }

    def opioid_naloxone_dosing(self, total_morphine_equivalent_mg: float) -> Dict:
        initial_dose = 0.04
        if total_morphine_equivalent_mg > 10:
            initial_dose = 0.4
        if total_morphine_equivalent_mg > 50:
            initial_dose = 2.0
        return {
            "initial_naloxone_mg": initial_dose,
            "route": "IV (preferred) or IM/intranasal",
            "repeat_every_2_3_min": True,
            "max_estimated_mg": round(total_morphine_equivalent_mg * 0.1, 2),
            "note": "Titrate to respirations > 8/min and SpO2 > 90%. Caution: precipitated withdrawal."
        }

    def carbon_monoxide_half_life(self, oxygen_fio2: float, cohb_percent: float) -> Dict:
        half_life = 320 / (oxygen_fio2 / 0.21) ** 1.5 if oxygen_fio2 > 0 else 320
        if half_life < 25:
            half_life = 23
        return {
            "fio2": oxygen_fio2,
            "cohb_percent": cohb_percent,
            "half_life_minutes": round(half_life, 1),
            "estimated_clearance_to_5pct_hours": round((math.log(cohb_percent / 5) / math.log(2)) * half_life / 60, 2) if cohb_percent > 5 else 0,
        }


def run():
    calc = PoisoningCalculator()

    print("=" * 60)
    print("Poisoning & Toxicology Calculator")
    print("=" * 60)

    profile = PoisoningProfile(
        poison_type=PoisonType.ACETAMINOPHEN,
        ingested_dose_mg=15000,
        weight_kg=70,
        time_since_exposure_hours=3,
        serum_level=45
    )
    result = calc.calculate(profile)
    print(f"\nAcetaminophen: {result.mg_per_kg} mg/kg, {result.toxicity_level.value}")
    print(f"Antidote: {result.antidote}")
    print(f"Charcoal: {result.activated_charcoal_indicated}, Dialysis: {result.hemodialysis_indicated}")
    nomogram = calc.acetaminophen_rumack_nomogram(4.0, 45.0)
    print(f"Rumack-Matthew: {nomogram}")

    profile2 = PoisoningProfile(
        poison_type=PoisonType.OPIOID,
        ingested_dose_mg=80,
        weight_kg=70,
        time_since_exposure_hours=0.5
    )
    result2 = calc.calculate(profile2)
    print(f"\nOpioid: {result2.mg_per_kg} mg/kg, {result2.toxicity_level.value}")
    naloxone = calc.opioid_naloxone_dosing(80)
    print(f"Naloxone: {naloxone}")

    co = calc.carbon_monoxide_half_life(1.0, 35.0)
    print(f"\nCO clearance: {co}")
    co_hbo = calc.carbon_monoxide_half_life(3.0, 35.0)
    print(f"CO clearance on 100% O2: {co_hbo}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
