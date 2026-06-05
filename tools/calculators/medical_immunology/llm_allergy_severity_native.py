"""
Allergy Severity Score Calculator — Immunology & Allergy
Allergic reaction grading (anaphylaxis severity) and epinephrine guidance.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class AllergySeverity(Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    ANAPHYLAXIS = "anaphylaxis"
    LIFE_THREATENING = "life_threatening"


@dataclass
class AllergyProfile:
    skin_urticaria: bool = False
    skin_angioedema: bool = False
    skin_pruritus: bool = False
    skin_flushing: bool = False
    respiratory_wheezing: bool = False
    respiratory_dyspnea: bool = False
    respiratory_stridor: bool = False
    respiratory_cough: bool = False
    respiratory_rhinorrhea: bool = False
    gastrointestinal_nausea: bool = False
    gastrointestinal_vomiting: bool = False
    gastrointestinal_diarrhea: bool = False
    gastrointestinal_cramps: bool = False
    cardiovascular_dizziness: bool = False
    cardiovascular_tachycardia: bool = False
    cardiovascular_hypotension: bool = False
    cardiovascular_collapse: bool = False
    neurological_sense_of_doom: bool = False
    neurological_confusion: bool = False
    neurological_loss_of_consciousness: bool = False
    known_allergen: str = ""
    trigger_route: str = "unknown"  # oral, inhalation, cutaneous, injection
    time_since_exposure_minutes: float = 0.0
    biphasic_history: bool = False
    asthma_history: bool = False
    cardiovascular_disease: bool = False
    beta_blocker_use: bool = False


@dataclass
class AllergyResult:
    severity: AllergySeverity
    score: int
    epinephrine_indicated: bool
    epinephrine_dose_mg: float
    epinephrine_route: str
    antihistamines_indicated: bool
    corticosteroids_indicated: bool
    iv_fluids_indicated: bool
    observation_hours: int
    biphasic_risk: str
    discharge_criteria: List[str]
    notes: List[str]


class AllergySeverityCalculator:
    """Allergic reaction severity grading and management."""

    def calculate(self, profile: AllergyProfile) -> AllergyResult:
        score = 0
        notes = []

        # Skin (1 point each)
        skin_score = sum([profile.skin_urticaria, profile.skin_angioedema,
                         profile.skin_pruritus, profile.skin_flushing])
        score += skin_score

        # Respiratory (2 points each)
        resp_score = sum([profile.respiratory_wheezing, profile.respiratory_dyspnea,
                         profile.respiratory_stridor, profile.respiratory_cough,
                         profile.respiratory_rhinorrhea]) * 2
        score += resp_score

        # GI (2 points each)
        gi_score = sum([profile.gastrointestinal_nausea, profile.gastrointestinal_vomiting,
                       profile.gastrointestinal_diarrhea, profile.gastrointestinal_cramps]) * 2
        score += gi_score

        # Cardiovascular (3 points each)
        cv_score = sum([profile.cardiovascular_dizziness, profile.cardiovascular_tachycardia,
                       profile.cardiovascular_hypotension, profile.cardiovascular_collapse]) * 3
        score += cv_score

        # Neurological (3 points each)
        neuro_score = sum([profile.neurological_sense_of_doom, profile.neurological_confusion,
                          profile.neurological_loss_of_consciousness]) * 3
        score += neuro_score

        # Severity classification
        if profile.cardiovascular_collapse or profile.neurological_loss_of_consciousness:
            severity = AllergySeverity.LIFE_THREATENING
        elif (profile.cardiovascular_hypotension or profile.respiratory_stridor or
              profile.respiratory_dyspnea or profile.neurological_confusion):
            severity = AllergySeverity.ANAPHYLAXIS
        elif cv_score >= 6 or resp_score >= 6 or gi_score >= 6:
            severity = AllergySeverity.SEVERE
        elif score >= 6:
            severity = AllergySeverity.MODERATE
        elif score >= 1:
            severity = AllergySeverity.MILD
        else:
            severity = None
            if severity is None:
                severity = AllergySeverity.MILD

        # Epinephrine criteria
        epi_indicated = severity.value in ["severe", "anaphylaxis", "life_threatening"]
        if profile.respiratory_dyspnea or profile.respiratory_stridor or profile.cardiovascular_hypotension:
            epi_indicated = True

        if epi_indicated:
            epi_dose = 0.3 if profile.cardiovascular_collapse or profile.cardiovascular_hypotension else 0.3
            epi_route = "IM (anterolateral thigh)" if not profile.cardiovascular_collapse else "IM/IV if hypotension"
            if profile.beta_blocker_use:
                notes.append("Beta-blocker use may blunt epinephrine response — glucagon 1-2mg IV may be needed.")
        else:
            epi_dose = 0.0
            epi_route = "Not indicated"

        # Antihistamines
        antihist = skin_score >= 1 or gi_score >= 2

        # Steroids
        steroids = severity.value in ["moderate", "severe", "anaphylaxis", "life_threatening"]

        # IV fluids
        iv_fluids = profile.cardiovascular_hypotension or profile.cardiovascular_collapse or profile.gastrointestinal_vomiting

        # Observation
        if severity.value == "life_threatening":
            obs = 24
        elif severity.value in ["anaphylaxis", "severe"]:
            obs = 8
        elif severity.value == "moderate":
            obs = 4
        else:
            obs = 1

        # Biphasic risk
        biphasic = "High" if (profile.biphasic_history or profile.time_since_exposure_minutes > 30) else "Moderate"
        if severity.value in ["anaphylaxis", "life_threatening"]:
            biphasic = "High"

        # Discharge criteria
        discharge = ["Symptom-free for observation period", "Vitals stable x 1 hour", "Patient education on trigger avoidance"]
        if severity.value in ["anaphylaxis", "life_threatening"]:
            discharge += ["Epinephrine auto-injector prescribed", "Allergy/immunology referral", "Action plan provided"]
        if epi_indicated:
            discharge.append("Epinephrine auto-injector training completed")

        if profile.asthma_history:
            notes.append("Asthma history increases risk of severe bronchospasm.")
        if profile.cardiovascular_disease:
            notes.append("Cardiovascular disease — epinephrine used cautiously, but benefits outweigh risks in anaphylaxis.")

        return AllergyResult(
            severity=severity,
            score=score,
            epinephrine_indicated=epi_indicated,
            epinephrine_dose_mg=epi_dose,
            epinephrine_route=epi_route,
            antihistamines_indicated=antihist,
            corticosteroids_indicated=steroids,
            iv_fluids_indicated=iv_fluids,
            observation_hours=obs,
            biphasic_risk=biphasic,
            discharge_criteria=discharge,
            notes=notes
        )

    def epinephrine_dosing_pediatric(self, weight_kg: float) -> dict:
        """Pediatric epinephrine auto-injector dosing."""
        if weight_kg < 7.5:
            return {"dose_mg": 0.1, "device": "Junior 0.1mg (if available) or IM drawn dose", " thigh": "anterolateral"}
        elif weight_kg < 15:
            return {"dose_mg": 0.1, "device": "Junior 0.1mg", "site": "anterolateral thigh"}
        elif weight_kg < 25:
            return {"dose_mg": 0.15, "device": "Junior 0.15mg", "site": "anterolateral thigh"}
        elif weight_kg < 30:
            return {"dose_mg": 0.15, "device": "Junior 0.15mg or adult 0.3mg", "site": "anterolateral thigh"}
        else:
            return {"dose_mg": 0.3, "device": "Adult 0.3mg", "site": "anterolateral thigh"}


def run():
    calc = AllergySeverityCalculator()

    print("=" * 60)
    print("Allergy Severity Score Calculator")
    print("=" * 60)

    profile = AllergyProfile(
        skin_urticaria=True, skin_angioedema=True,
        respiratory_dyspnea=True, respiratory_wheezing=True,
        cardiovascular_tachycardia=True, cardiovascular_dizziness=True,
        gastrointestinal_vomiting=True,
        time_since_exposure_minutes=15,
        asthma_history=True
    )

    result = calc.calculate(profile)
    print(f"\nSeverity: {result.severity.value}")
    print(f"Score: {result.score}")
    print(f"Epinephrine: {result.epinephrine_indicated} {result.epinephrine_dose_mg}mg {result.epinephrine_route}")
    print(f"Antihistamines: {result.antihistamines_indicated}")
    print(f"Steroids: {result.corticosteroids_indicated}")
    print(f"IV fluids: {result.iv_fluids_indicated}")
    print(f"Observation: {result.observation_hours} hours")
    print(f"Biphasic risk: {result.biphasic_risk}")
    print(f"Notes: {result.notes}")

    print(f"\nPediatric epinephrine (20kg): {calc.epinephrine_dosing_pediatric(20)}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
