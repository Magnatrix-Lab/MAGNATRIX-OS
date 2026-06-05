"""
Liver Fibrosis Calculator — Hepatology
FIB-4, APRI, and NAFLD fibrosis scoring.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List, Dict
from enum import Enum


class FibrosisStage(Enum):
    F0_F1 = "no_minimal_fibrosis"
    F2 = "significant_fibrosis"
    F3 = "advanced_fibrosis"
    F4 = "cirrhosis"


@dataclass
class FibrosisProfile:
    age: int
    ast_u_l: float
    alt_u_l: float
    platelets_k_u_l: float
    bmi: float = 25.0
    diabetes: bool = False
    albumin_g_dl: float = 4.0
    bilirubin_mg_dl: float = 1.0
    etiology: str = "unknown"  # nafld, hepatitis_c, hepatitis_b, alcohol


@dataclass
class FibrosisResult:
    fib4_score: float
    apri_score: float
    nafld_fibrosis_score: float
    fibrosis_stage: str
    fib4_interpretation: str
    apri_interpretation: str
    recommendations: List[str]
    follow_up: str


class LiverFibrosisCalculator:
    """Non-invasive liver fibrosis assessment."""

    def calculate(self, profile: FibrosisProfile) -> FibrosisResult:
        # FIB-4
        fib4 = (profile.age * profile.ast_u_l) / (profile.platelets_k_u_l * (profile.alt_u_l ** 0.5))

        # APRI
        apri = ((profile.ast_u_l / 40) * 100) / profile.platelets_k_u_l

        # NAFLD Fibrosis Score
        nfs = (-1.675 + 0.037 * profile.age + 0.094 * profile.bmi +
               1.13 * (1 if profile.diabetes else 0) + 0.99 * (profile.ast_u_l / profile.alt_u_l) -
               0.013 * profile.platelets_k_u_l - 0.66 * profile.albumin_g_dl)

        # Interpretations
        if fib4 < 1.3:
            fib4_interp = "Low probability of advanced fibrosis (F0-F1 likely)"
        elif fib4 < 2.67:
            fib4_interp = "Indeterminate — consider elastography or biopsy"
        else:
            fib4_interp = "High probability of advanced fibrosis/cirrhosis (F3-F4)"

        if apri < 0.5:
            apri_interp = "Low probability of significant fibrosis"
        elif apri < 1.0:
            apri_interp = "Indeterminate"
        else:
            apri_interp = "High probability of significant fibrosis/cirrhosis"

        # Stage determination
        if fib4 < 1.3 and apri < 0.5:
            stage = "F0-F1 (No/Minimal fibrosis)"
        elif fib4 > 2.67 or apri > 1.0:
            stage = "F3-F4 (Advanced fibrosis/Cirrhosis)"
        elif fib4 > 1.3 or apri > 0.5:
            stage = "F2 (Significant fibrosis)"
        else:
            stage = "Indeterminate"

        recs = ["Hepatology referral if F2 or higher", "Alcohol abstinence", "Weight management if NAFLD"]
        if profile.diabetes:
            recs.append("Optimize glycemic control — metformin preferred")
        if profile.etiology == "nafld":
            recs += ["Lifestyle intervention (7-10% weight loss)", "Consider vitamin E if non-diabetic NASH"]
        if profile.etiology in ["hepatitis_c", "hepatitis_b"]:
            recs.append("Antiviral therapy evaluation — DAA for HCV, TDF/ETV for HBV")

        follow = "Repeat FIB-4 annually if stable" if "F0-F1" in stage else "Elastography (FibroScan) or liver biopsy in 3-6 months"

        return FibrosisResult(
            fib4_score=round(fib4, 2),
            apri_score=round(apri, 2),
            nafld_fibrosis_score=round(nfs, 2),
            fibrosis_stage=stage,
            fib4_interpretation=fib4_interp,
            apri_interpretation=apri_interp,
            recommendations=recs,
            follow_up=follow
        )


def run():
    calc = LiverFibrosisCalculator()

    print("=" * 60)
    print("Liver Fibrosis Calculator")
    print("=" * 60)

    profile = FibrosisProfile(
        age=55, ast_u_l=45, alt_u_l=38, platelets_k_u_l=180,
        bmi=32, diabetes=True, albumin_g_dl=3.8, etiology="nafld"
    )

    result = calc.calculate(profile)
    print(f"\nFIB-4: {result.fib4_score} — {result.fib4_interpretation}")
    print(f"APRI: {result.apri_score} — {result.apri_interpretation}")
    print(f"NAFLD Score: {result.nafld_fibrosis_score}")
    print(f"Stage: {result.fibrosis_stage}")
    print(f"Recommendations: {result.recommendations}")
    print(f"Follow-up: {result.follow_up}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
