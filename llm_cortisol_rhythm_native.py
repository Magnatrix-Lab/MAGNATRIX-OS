"""
Cortisol Rhythm Calculator — Endocrinology
Cortisol circadian rhythm assessment and Cushing syndrome screening.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List, Dict


@dataclass
class CortisolProfile:
    morning_cortisol_mcg_dl: float   # 8 AM (normal 6-23)
    afternoon_cortisol_mcg_dl: float  # 4 PM (normal 3-13)
    midnight_cortisol_mcg_dl: float  # 11 PM (normal < 5)
    dexamethasone_1mg_overnight: bool = False  # Test performed?
    post_dexamethasone_cortisol: float = 0.0  # Should suppress < 1.8
    acth_level_pg_ml: float = 0.0
    urine_free_cortisol_24h: float = 0.0  # mcg/24h (normal < 100)


@dataclass
class CortisolResult:
    circadian_intact: bool
    cushing_suspected: bool
    cushing_likelihood: str
    acth_dependent: bool
    recommendations: List[str]
    follow_up_tests: List[str]
    notes: List[str]


class CortisolCalculator:
    """Cortisol rhythm assessment and Cushing syndrome screening."""

    def calculate(self, profile: CortisolProfile) -> CortisolResult:
        notes = []
        recs = []

        # Circadian rhythm check
        circadian = (profile.morning_cortisol_mcg_dl > profile.afternoon_cortisol_mcg_dl and
                     profile.afternoon_cortisol_mcg_dl > profile.midnight_cortisol_mcg_dl)

        if not circadian:
            notes.append("Loss of diurnal cortisol rhythm — abnormal.")

        # Cushing screening
        cushing_suspected = False
        cushing_likelihood = "Unlikely"

        if profile.midnight_cortisol_mcg_dl > 5:
            cushing_suspected = True
            notes.append("Midnight salivary cortisol elevated — suggests loss of nadir suppression.")

        if profile.urine_free_cortisol_24h > 100:
            cushing_suspected = True
            notes.append(f"24h urine free cortisol elevated ({profile.urine_free_cortisol_24h} mcg/24h).")

        if profile.dexamethasone_1mg_overnight and profile.post_dexamethasone_cortisol > 1.8:
            cushing_suspected = True
            notes.append("Failed 1mg overnight dexamethasone suppression test.")

        if cushing_suspected:
            if (profile.midnight_cortisol_mcg_dl > 5 and profile.urine_free_cortisol_24h > 100 and
                profile.dexamethasone_1mg_overnight and profile.post_dexamethasone_cortisol > 1.8):
                cushing_likelihood = "High"
            else:
                cushing_likelihood = "Moderate"

        # ACTH-dependent vs independent
        acth_dependent = None
        if cushing_suspected and profile.acth_level_pg_ml > 0:
            acth_dependent = profile.acth_level_pg_ml > 10
            if acth_dependent:
                notes.append("ACTH elevated — ACTH-dependent Cushing (pituitary or ectopic).")
            else:
                notes.append("ACTH suppressed — ACTH-independent Cushing (adrenal).")

        if cushing_suspected:
            recs.append("Endocrinology referral for Cushing workup")
            follow_up = ["Low-dose dexamethasone suppression test (formal)", "Late-night salivary cortisol (x2)", "24h urine free cortisol (x2)", "ACTH level", "Pituitary MRI if ACTH-dependent", "Adrenal CT if ACTH-independent"]
        else:
            follow_up = ["Repeat cortisol if symptoms persist", "Rule out exogenous steroid use"]

        if not cushing_suspected and not circadian:
            recs.append("Stress, sleep disruption, or shift work can flatten cortisol rhythm")
            follow_up.append("Sleep hygiene assessment", "Stress management evaluation")

        return CortisolResult(
            circadian_intact=circadian,
            cushing_suspected=cushing_suspected,
            cushing_likelihood=cushing_likelihood,
            acth_dependent=acth_dependent,
            recommendations=recs,
            follow_up_tests=follow_up,
            notes=notes
        )


def run():
    calc = CortisolCalculator()

    print("=" * 60)
    print("Cortisol Rhythm Calculator")
    print("=" * 60)

    cases = [
        CortisolProfile(18, 8, 2.5, True, 0.8, acth_level_pg_ml=15),
        CortisolProfile(28, 25, 12, True, 5.5, acth_level_pg_ml=8, urine_free_cortisol_24h=180),
    ]

    for i, c in enumerate(cases, 1):
        result = calc.calculate(c)
        print(f"\nCase {i}: Morning={c.morning_cortisol_mcg_dl}, Midnight={c.midnight_cortisol_mcg_dl}")
        print(f"  Circadian intact: {result.circadian_intact}")
        print(f"  Cushing suspected: {result.cushing_suspected} ({result.cushing_likelihood})")
        print(f"  ACTH-dependent: {result.acth_dependent}")
        print(f"  Notes: {result.notes}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
