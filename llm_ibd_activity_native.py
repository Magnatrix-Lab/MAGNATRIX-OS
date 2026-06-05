"""
IBD Activity Calculator — Gastroenterology
Crohn's (CDAI) and Ulcerative Colitis (Mayo) scoring.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class IBDType(Enum):
    CROHN = "crohn"
    ULCERATIVE_COLITIS = "uc"


@dataclass
class IBDProfile:
    ibd_type: IBDType
    # CDAI variables
    stool_count_per_day: int = 0
    abdominal_pain_score: int = 0  # 0-3
    general_well_being: int = 0    # 0-4 (0=well, 4=terrible)
    extraintestinal_manifestations: int = 0  # 0-3 per type
    opiates: bool = False
    abdominal_mass: bool = False
    hematocrit_percent: float = 40.0
    weight_deviation_percent: float = 0.0
    # Mayo variables (UC)
    stool_frequency_score: int = 0  # 0-3
    rectal_bleeding_score: int = 0  # 0-3
    endoscopy_findings: int = 0     # 0-3
    physician_global_assessment: int = 0  # 0-3


@dataclass
class IBDResult:
    score: float
    score_name: str
    severity: str
    remission: bool
    treatment_step: str
    recommendations: List[str]
    follow_up: str


class IBDCalculator:
    """IBD activity scoring for Crohn's and Ulcerative Colitis."""

    def calculate(self, profile: IBDProfile) -> IBDResult:
        if profile.ibd_type == IBDType.CROHN:
            # CDAI calculation
            cdai = (profile.stool_count_per_day * 7 +
                    profile.abdominal_pain_score * 7 +
                    profile.general_well_being * 7 +
                    profile.extraintestinal_manifestations * 20 +
                    (30 if profile.opiates else 0) +
                    (10 if profile.abdominal_mass else 0) +
                    max(0, (100 - profile.hematocrit_percent) * 6) +
                    max(0, profile.weight_deviation_percent * 1))

            score = cdai
            score_name = "CDAI"
            if cdai < 150:
                severity = "Remission"
                remission = True
                step = "Maintenance therapy"
            elif cdai < 220:
                severity = "Mild"
                remission = False
                step = "Budesonide or 5-ASA if colonic"
            elif cdai < 450:
                severity = "Moderate"
                remission = False
                step = "Systemic corticosteroids + immunomodulator (azathioprine/MTX)"
            else:
                severity = "Severe"
                remission = False
                step = "Anti-TNF (infliximab/adalimumab) or surgery"

        else:
            # Mayo score for UC
            mayo = (profile.stool_frequency_score +
                    profile.rectal_bleeding_score +
                    profile.endoscopy_findings +
                    profile.physician_global_assessment)

            score = mayo
            score_name = "Mayo Score"
            if mayo <= 2:
                severity = "Remission"
                remission = True
                step = "Maintenance 5-ASA or immunomodulator"
            elif mayo <= 5:
                severity = "Mild"
                remission = False
                step = "5-ASA + topical mesalamine"
            elif mayo <= 7:
                severity = "Moderate"
                remission = False
                step = "Systemic steroids + 5-ASA; consider anti-TNF"
            else:
                severity = "Severe"
                remission = False
                step = "IV steroids + anti-TNF; colectomy if refractory"

        recs = ["Smoking cessation (if Crohn's)", "Nutritional assessment", "Vitamin D/B12/folate monitoring"]
        if not remission:
            recs += ["Steroid-sparing strategy", "Monitor for infection (TB, hepatitis) before biologics"]
        if severity == "Severe":
            recs += ["Surgical consultation if refractory", "Colonoscopy surveillance every 1-2 years"]

        return IBDResult(
            score=round(score, 1),
            score_name=score_name,
            severity=severity,
            remission=remission,
            treatment_step=step,
            recommendations=recs,
            follow_up="Every 3-6 months if active; annually if remission"
        )


def run():
    calc = IBDCalculator()

    print("=" * 60)
    print("IBD Activity Calculator")
    print("=" * 60)

    crohn = IBDProfile(
        IBDType.CROHN,
        stool_count_per_day=4, abdominal_pain_score=2, general_well_being=3,
        extraintestinal_manifestations=1, opiates=False, abdominal_mass=False,
        hematocrit_percent=35, weight_deviation_percent=-8
    )
    result = calc.calculate(crohn)
    print(f"\nCrohn's: {result.score_name} = {result.score}")
    print(f"  Severity: {result.severity}, Remission: {result.remission}")
    print(f"  Step: {result.treatment_step}")

    uc = IBDProfile(
        IBDType.ULCERATIVE_COLITIS,
        stool_frequency_score=2, rectal_bleeding_score=2,
        endoscopy_findings=2, physician_global_assessment=2
    )
    result2 = calc.calculate(uc)
    print(f"\nUC: {result2.score_name} = {result2.score}")
    print(f"  Severity: {result2.severity}, Remission: {result2.remission}")
    print(f"  Step: {result2.treatment_step}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
