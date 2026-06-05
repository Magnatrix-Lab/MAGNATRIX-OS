"""
IPSS Calculator — Urology
International Prostate Symptom Score and BPH management.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class IPSSSeverity(Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


@dataclass
class IPSSProfile:
    # Each scored 0-5: 0=not at all, 1=less than 1 in 5, 2=less than half, 3=about half, 4=more than half, 5=almost always
    incomplete_emptying: int        # Q1
    frequency: int                   # Q2
    intermittency: int               # Q3
    urgency: int                     # Q4
    weak_stream: int                 # Q5
    straining: int                   # Q6
    nocturia: int                    # Q7 (0-5)
    quality_of_life_score: int = 0   # BPH QoL (0-6)


@dataclass
class IPSSResult:
    total_score: int
    severity: IPSSSeverity
    storage_symptoms: int
    voiding_symptoms: int
    post_micturition: int  # Not applicable in standard IPSS but useful
    quality_of_life: str
    treatment_recommended: List[str]
    follow_up: str


class IPSSCalculator:
    """International Prostate Symptom Score calculator."""

    def calculate(self, profile: IPSSProfile) -> IPSSResult:
        # Validate ranges
        scores = [profile.incomplete_emptying, profile.frequency, profile.intermittency,
                  profile.urgency, profile.weak_stream, profile.straining, profile.nocturia]
        scores = [max(0, min(5, s)) for s in scores]
        total = sum(scores)

        if total <= 7:
            severity = IPSSSeverity.MILD
        elif total <= 19:
            severity = IPSSSeverity.MODERATE
        else:
            severity = IPSSSeverity.SEVERE

        # Subscores
        storage = scores[1] + scores[3] + scores[6]  # frequency + urgency + nocturia
        voiding = scores[0] + scores[2] + scores[4] + scores[5]  # emptying + intermittency + weak stream + straining

        # QoL interpretation
        qol = profile.quality_of_life_score
        if qol <= 2:
            qol_interp = "Satisfied / Pleased"
        elif qol <= 4:
            qol_interp = "Mixed / Mostly dissatisfied"
        else:
            qol_interp = "Unhappy / Terrible"

        recs = []
        if severity == IPSSSeverity.MILD:
            recs = ["Watchful waiting", "Lifestyle modifications (fluid restriction, avoid caffeine/alcohol)"]
        elif severity == IPSSSeverity.MODERATE:
            recs = ["Alpha-blocker (tamsulosin/alfuzosin)", "5-alpha-reductase inhibitor if prostate > 40g"]
            if qol >= 4:
                recs.append("Consider surgical options if medication fails")
        else:
            recs = ["Alpha-blocker + 5-ARI combination", "Surgical evaluation (TURP, HoLEP, laser)"]
            if scores[4] >= 4:  # weak stream severe
                recs.append("Severe weak stream — surgical intervention likely needed")

        if profile.urgency >= 4:
            recs.append("Anticholinergic (solifenacin/tolterodine) if no retention risk")
        if profile.nocturia >= 3:
            recs.append("Nocturia management: evening fluid restriction, desmopressin if no hyponatremia risk")

        return IPSSResult(
            total_score=total,
            severity=severity,
            storage_symptoms=storage,
            voiding_symptoms=voiding,
            post_micturition=0,
            quality_of_life=qol_interp,
            treatment_recommended=recs,
            follow_up="Reassess IPSS in 4-12 weeks after initiating therapy"
        )

    def bph_progression_risk(self, age: int, psa_ng_ml: float, prostate_volume_ml: float) -> dict:
        """Estimate risk of BPH progression."""
        risk = 0
        if age > 70:
            risk += 2
        if psa_ng_ml > 1.5:
            risk += 2
        if prostate_volume_ml > 40:
            risk += 2
        if risk >= 5:
            return {"risk": "High", "action": "5-ARI strongly indicated to prevent progression"}
        elif risk >= 3:
            return {"risk": "Moderate", "action": "Consider 5-ARI if symptomatic"}
        else:
            return {"risk": "Low", "action": "Alpha-blocker sufficient"}


def run():
    calc = IPSSCalculator()

    print("=" * 60)
    print("IPSS Calculator")
    print("=" * 60)

    profile = IPSSProfile(
        incomplete_emptying=3, frequency=3, intermittency=2,
        urgency=4, weak_stream=4, straining=3, nocturia=3,
        quality_of_life_score=4
    )

    result = calc.calculate(profile)
    print(f"\nTotal IPSS: {result.total_score}")
    print(f"Severity: {result.severity.value}")
    print(f"Storage: {result.storage_symptoms}, Voiding: {result.voiding_symptoms}")
    print(f"QoL: {result.quality_of_life}")
    print(f"Treatment: {result.treatment_recommended}")

    print(f"\nBPH progression risk (65yo, PSA 2.5, PV 55ml): {calc.bph_progression_risk(65, 2.5, 55)}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
