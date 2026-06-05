"""
Performance Status Calculator — Oncology
ECOG and Karnofsky scoring with prognostic implications.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class PerformanceProfile:
    ecog_score: int  # 0-4
    karnofsky_score: int  # 0-100
    age: int = 60
    comorbidities: List[str] = None
    weight_loss_percent_6mo: float = 0.0
    albumin_g_dl: float = 3.5

    def __post_init__(self):
        if self.comorbidities is None:
            self.comorbidities = []


@dataclass
class PerformanceResult:
    ecog_interpretation: str
    karnofsky_interpretation: str
    prognosis_category: str
    treatment_eligibility: str
    trial_eligibility: str
    estimated_survival_months: str
    recommendations: List[str]


class PerformanceStatusCalculator:
    """ECOG and Karnofsky performance status interpreter."""

    ECOG_MAP = {
        0: "Fully active, no restrictions",
        1: "Ambulatory, restricted in strenuous activity",
        2: "Ambulatory, up >50% of waking hours, can self-care",
        3: "Capable of limited self-care, confined to bed/chair >50% of time",
        4: "Completely disabled, cannot self-care, confined to bed/chair"
    }

    KARNOFSKY_MAP = {
        100: "Normal, no complaints",
        90: "Able to carry on normal activity, minor symptoms",
        80: "Normal activity with effort, some symptoms",
        70: "Cares for self, unable to carry on normal activity",
        60: "Requires occasional assistance",
        50: "Requires considerable assistance, frequent medical care",
        40: "Disabled, requires special care",
        30: "Severely disabled, hospitalization indicated",
        20: "Very sick, active supportive treatment needed",
        10: "Moribund, fatal processes progressing",
        0: "Dead"
    }

    def calculate(self, profile: PerformanceProfile) -> PerformanceResult:
        ecog_interp = self.ECOG_MAP.get(profile.ecog_score, "Invalid score")
        karnofsky_interp = self.KARNOFSKY_MAP.get(
            max([k for k in self.KARNOFSKY_MAP if k <= profile.karnofsky_score], default=0),
            "Invalid score"
        )

        # Prognosis
        if profile.ecog_score <= 1:
            if profile.albumin_g_dl >= 3.5 and profile.weight_loss_percent_6mo < 5:
                prog = "Good prognosis"
                survival = "12+ months (varies by cancer type)"
            else:
                prog = "Moderate prognosis"
                survival = "6-12 months"
        elif profile.ecog_score == 2:
            prog = "Fair prognosis"
            survival = "3-6 months"
        elif profile.ecog_score == 3:
            prog = "Poor prognosis"
            survival = "1-3 months"
        else:
            prog = "Very poor prognosis"
            survival = "<1 month"

        # Treatment eligibility
        if profile.ecog_score <= 2:
            treat = "Eligible for standard chemotherapy / radiation"
        elif profile.ecog_score == 3:
            treat = "Consider reduced-intensity or palliative treatment only"
        else:
            treat = "Not eligible for cytotoxic therapy — best supportive care"

        # Trial eligibility
        if profile.ecog_score <= 1:
            trial = "Eligible for most clinical trials"
        elif profile.ecog_score == 2:
            trial = "Eligible for some trials (check protocol-specific criteria)"
        else:
            trial = "Generally not eligible for clinical trials"

        recs = ["Nutritional support assessment", "Physical therapy evaluation"]
        if profile.weight_loss_percent_6mo > 10:
            recs.append("Significant weight loss — nutrition intervention, consider megestrol or appetite stimulants")
        if profile.albumin_g_dl < 3.0:
            recs.append("Hypoalbuminemia — poor prognostic factor, nutritional support")
        if profile.ecog_score >= 3:
            recs += ["Palliative care consultation", "Advance care planning discussion"]
        if profile.ecog_score <= 1:
            recs.append("Maintain physical activity as tolerated")

        return PerformanceResult(
            ecog_interpretation=ecog_interp,
            karnofsky_interpretation=karnofsky_interp,
            prognosis_category=prog,
            treatment_eligibility=treat,
            trial_eligibility=trial,
            estimated_survival_months=survival,
            recommendations=recs
        )

    def convert_ecog_to_karnofsky(self, ecog: int) -> int:
        mapping = {0: 100, 1: 80, 2: 60, 3: 40, 4: 20}
        return mapping.get(ecog, 0)

    def convert_karnofsky_to_ecog(self, karnofsky: int) -> int:
        if karnofsky >= 80:
            return 0 if karnofsky >= 90 else 1
        elif karnofsky >= 60:
            return 2
        elif karnofsky >= 40:
            return 3
        else:
            return 4


def run():
    calc = PerformanceStatusCalculator()

    print("=" * 60)
    print("Performance Status Calculator")
    print("=" * 60)

    cases = [
        PerformanceProfile(0, 90, 55, [], 0, 4.0),
        PerformanceProfile(2, 60, 70, ["COPD", "diabetes"], 8, 3.0),
        PerformanceProfile(3, 40, 78, ["CHF"], 15, 2.5),
    ]

    for i, c in enumerate(cases, 1):
        result = calc.calculate(c)
        print(f"\nCase {i}: ECOG {c.ecog_score}, Karnofsky {c.karnofsky_score}")
        print(f"  ECOG: {result.ecog_interpretation}")
        print(f"  Prognosis: {result.prognosis_category}")
        print(f"  Survival estimate: {result.estimated_survival_months}")
        print(f"  Treatment: {result.treatment_eligibility}")
        print(f"  Trial: {result.trial_eligibility}")
        print(f"  Recs: {result.recommendations}")

    print(f"\nECOG 1 -> Karnofsky: {calc.convert_ecog_to_karnofsky(1)}")
    print(f"Karnofsky 70 -> ECOG: {calc.convert_karnofsky_to_ecog(70)}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
