"""
Histamine Response Calculator — Immunology
Mast cell activation, histamine intolerance scoring, and DAO enzyme assessment.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class HistamineLevel(Enum):
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class HistamineProfile:
    serum_histamine_ng_ml: float
    diamine_oxidase_u_ml: float
    histamine_n_methyltransferase_u_ml: float = 0.0
    symptom_score: int = 0  # 0-30
    dietary_histamine_mg_day: float = 0.0
    medications_affecting_dao: List[str] = None  # NSAIDs, antihistamines, etc.
    gi_symptoms: bool = False
    skin_symptoms: bool = False
    respiratory_symptoms: bool = False
    cardiovascular_symptoms: bool = False
    neurological_symptoms: bool = False

    def __post_init__(self):
        if self.medications_affecting_dao is None:
            self.medications_affecting_dao = []


@dataclass
class HistamineResult:
    histamine_level: HistamineLevel
    dao_status: str
    histamine_intolerance_likely: bool
    mast_cell_activation_suspected: bool
    dietary_recommendations: List[str]
    supplement_recommendations: List[str]
    follow_up_tests: List[str]
    notes: List[str]


class HistamineCalculator:
    """Histamine metabolism and intolerance assessment."""

    def calculate(self, profile: HistamineProfile) -> HistamineResult:
        notes = []

        # Serum histamine levels
        if profile.serum_histamine_ng_ml < 1:
            h_level = HistamineLevel.NORMAL
        elif profile.serum_histamine_ng_ml < 3:
            h_level = HistamineLevel.ELEVATED
        elif profile.serum_histamine_ng_ml < 8:
            h_level = HistamineLevel.HIGH
        else:
            h_level = HistamineLevel.CRITICAL

        # DAO status
        if profile.diamine_oxidase_u_ml < 10:
            dao_status = "Severely deficient"
            notes.append("DAO deficiency strongly suggests histamine intolerance.")
        elif profile.diamine_oxidase_u_ml < 40:
            dao_status = "Low"
        elif profile.diamine_oxidase_u_ml < 80:
            dao_status = "Borderline"
        else:
            dao_status = "Normal"

        # Histamine intolerance
        hist_intolerance = (profile.diamine_oxidase_u_ml < 40 and profile.serum_histamine_ng_ml > 1 and
                           profile.symptom_score >= 5)

        # Mast cell activation syndrome (MCAS)
        mcas_suspected = (profile.serum_histamine_ng_ml > 3 and profile.symptom_score >= 10 and
                         sum([profile.gi_symptoms, profile.skin_symptoms, profile.respiratory_symptoms,
                              profile.cardiovascular_symptoms, profile.neurological_symptoms]) >= 3)

        if mcas_suspected:
            notes.append("Multi-system symptoms + elevated histamine suggests MCAS.")

        # Dietary recommendations
        diet_recs = []
        if hist_intolerance or mcas_suspected:
            diet_recs = [
                "Avoid aged cheeses, fermented foods, cured meats, wine, vinegar",
                "Avoid histamine-releasing foods: strawberries, citrus, tomatoes, chocolate",
                "Freshly prepared meals — avoid leftovers > 24 hours",
                "Low-histamine diet trial for 2-4 weeks"
            ]
        if profile.dietary_histamine_mg_day > 50:
            diet_recs.append("Estimated dietary histamine >50mg/day — reduce to <20mg/day for trial")

        # Supplements
        supp_recs = []
        if profile.diamine_oxidase_u_ml < 40:
            supp_recs += ["DAO enzyme supplement (1-2 capsules before meals)", "Vitamin B6 (cofactor for DAO)", "Vitamin C (stabilizes mast cells)"]
        if mcas_suspected:
            supp_recs += ["Quercetin (mast cell stabilizer)", "Luteolin", "Omega-3 fatty acids"]
        if profile.neurological_symptoms:
            supp_recs.append("Magnesium glycinate (neurological support)")

        # Medication interactions
        if "NSAIDs" in profile.medications_affecting_dao:
            notes.append("NSAIDs inhibit DAO — avoid if histamine intolerance suspected.")
        if "antihistamines" in profile.medications_affecting_dao:
            notes.append("Antihistamines may mask symptoms but do not address DAO deficiency.")

        follow_up = ["24-hour urine N-methylhistamine", "Serum tryptase during flare", "Chromogranin A"]
        if mcas_suspected:
            follow_up += ["Bone marrow biopsy if severe", "KIT D816V mutation testing", "Comprehensive mediator profile"]
        if hist_intolerance:
            follow_up += ["Elimination diet challenge with symptom diary", "Repeat DAO after 4-week diet trial"]

        return HistamineResult(
            histamine_level=h_level,
            dao_status=dao_status,
            histamine_intolerance_likely=hist_intolerance,
            mast_cell_activation_suspected=mcas_suspected,
            dietary_recommendations=diet_recs,
            supplement_recommendations=supp_recs,
            follow_up_tests=follow_up,
            notes=notes
        )


def run():
    calc = HistamineCalculator()

    print("=" * 60)
    print("Histamine Response Calculator")
    print("=" * 60)

    profile = HistamineProfile(
        serum_histamine_ng_ml=4.5, diamine_oxidase_u_ml=18,
        symptom_score=14, dietary_histamine_mg_day=80,
        gi_symptoms=True, skin_symptoms=True, respiratory_symptoms=True,
        cardiovascular_symptoms=False, neurological_symptoms=True,
        medications_affecting_dao=["NSAIDs"]
    )

    result = calc.calculate(profile)
    print(f"\nHistamine level: {result.histamine_level.value}")
    print(f"DAO status: {result.dao_status}")
    print(f"Histamine intolerance: {result.histamine_intolerance_likely}")
    print(f"MCAS suspected: {result.mast_cell_activation_suspected}")
    print(f"Dietary: {result.dietary_recommendations}")
    print(f"Supplements: {result.supplement_recommendations}")
    print(f"Follow-up: {result.follow_up_tests}")
    print(f"Notes: {result.notes}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
