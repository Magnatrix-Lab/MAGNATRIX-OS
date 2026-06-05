"""
Child-Pugh Score Calculator — Hepatology
Cirrhosis severity scoring and prognosis estimation.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class ChildPughClass(Enum):
    A = "A"
    B = "B"
    C = "C"


@dataclass
class ChildPughProfile:
    bilirubin_mg_dl: float
    albumin_g_dl: float
    inr: float
    ascites: str  # "none", "mild", "severe"
    hepatic_encephalopathy_grade: int  # 0-4


@dataclass
class ChildPughResult:
    score: int
    classification: ChildPughClass
    one_year_survival: float
    two_year_survival: float
    percutaneous_procedure_safe: bool
    transplant_evaluation: bool
    recommendations: List[str]


class ChildPughCalculator:
    """Child-Pugh score for cirrhosis severity."""

    def calculate(self, profile: ChildPughProfile) -> ChildPughResult:
        score = 0

        # Bilirubin
        if profile.bilirubin_mg_dl < 2:
            score += 1
        elif profile.bilirubin_mg_dl <= 3:
            score += 2
        else:
            score += 3

        # Albumin
        if profile.albumin_g_dl > 3.5:
            score += 1
        elif profile.albumin_g_dl >= 2.8:
            score += 2
        else:
            score += 3

        # INR
        if profile.inr < 1.7:
            score += 1
        elif profile.inr <= 2.3:
            score += 2
        else:
            score += 3

        # Ascites
        if profile.ascites == "none":
            score += 1
        elif profile.ascites == "mild":
            score += 2
        else:
            score += 3

        # Encephalopathy
        if profile.hepatic_encephalopathy_grade == 0:
            score += 1
        elif profile.hepatic_encephalopathy_grade in [1, 2]:
            score += 2
        else:
            score += 3

        # Classification
        if score <= 6:
            classification = ChildPughClass.A
            one_year = 100.0
            two_year = 85.0
            procedure_safe = True
            transplant = False
        elif score <= 9:
            classification = ChildPughClass.B
            one_year = 80.0
            two_year = 60.0
            procedure_safe = False
            transplant = False
        else:
            classification = ChildPughClass.C
            one_year = 45.0
            two_year = 35.0
            procedure_safe = False
            transplant = True

        recs = ["Hepatology follow-up", "Avoid hepatotoxic drugs (NSAIDs, acetaminophen > 2g/day)", "Alcohol abstinence"]
        if classification == ChildPughClass.B:
            recs += ["Paracentesis if ascites symptomatic", "Lactulose + rifaximin if encephalopathy"]
        if classification == ChildPughClass.C:
            recs += ["Transplant evaluation urgently", "Beta-blocker for variceal prophylaxis if indicated", "Nutrition support"]
        if profile.ascites != "none":
            recs.append("Sodium restriction < 2g/day, diuretics (spironolactone + furosemide)")
        if profile.hepatic_encephalopathy_grade > 0:
            recs.append("Lactulose titrated to 2-3 soft stools/day")

        return ChildPughResult(
            score=score,
            classification=classification,
            one_year_survival=one_year,
            two_year_survival=two_year,
            percutaneous_procedure_safe=procedure_safe,
            transplant_evaluation=transplant,
            recommendations=recs
        )


def run():
    calc = ChildPughCalculator()

    print("=" * 60)
    print("Child-Pugh Score Calculator")
    print("=" * 60)

    cases = [
        ChildPughProfile(1.5, 3.8, 1.4, "none", 0),
        ChildPughProfile(3.5, 2.5, 2.1, "mild", 1),
        ChildPughProfile(6.0, 2.0, 3.0, "severe", 3),
    ]

    for i, c in enumerate(cases, 1):
        result = calc.calculate(c)
        print(f"\nCase {i}: Score = {result.score}, Class = {result.classification.value}")
        print(f"  1yr survival: {result.one_year_survival}%, 2yr: {result.two_year_survival}%")
        print(f"  Procedure safe: {result.percutaneous_procedure_safe}")
        print(f"  Transplant eval: {result.transplant_evaluation}")
        print(f"  Recs: {result.recommendations}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
