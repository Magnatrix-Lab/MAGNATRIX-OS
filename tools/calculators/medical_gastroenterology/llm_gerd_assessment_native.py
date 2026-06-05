"""
GERD Assessment Calculator — Gastroenterology
Reflux symptom scoring, severity, and management guidance.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class GERDSeverity(Enum):
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


@dataclass
class GERDProfile:
    heartburn_frequency_per_week: int
    heartburn_severity: int  # 1-10
    regurgitation_frequency_per_week: int
    chest_pain: bool = False
    dysphagia: bool = False
    odynophagia: bool = False
    chronic_cough: bool = False
    hoarseness: bool = False
    dental_erosion: bool = False
    alarm_symptoms: List[str] = None  # weight loss, anemia, vomiting, GI bleeding
    ppi_response: str = "unknown"  # good, partial, none
    duration_years: float = 0.0

    def __post_init__(self):
        if self.alarm_symptoms is None:
            self.alarm_symptoms = []


@dataclass
class GERDResult:
    score: int
    severity: GERDSeverity
    alarm_symptoms_present: bool
    endoscopy_recommended: bool
    ppi_trial_recommended: bool
    surgery_candidate: bool
    management: List[str]
    follow_up: str


class GERDCalculator:
    """GERD symptom assessment and management guidance."""

    def calculate(self, profile: GERDProfile) -> GERDResult:
        score = 0

        # Frequency
        score += min(profile.heartburn_frequency_per_week, 7) * 2
        score += min(profile.regurgitation_frequency_per_week, 7) * 2

        # Severity
        score += profile.heartburn_severity

        # Extra-esophageal symptoms
        if profile.chest_pain:
            score += 2
        if profile.chronic_cough:
            score += 2
        if profile.hoarseness:
            score += 2
        if profile.dental_erosion:
            score += 1

        # Dysphagia / odynophagia (alarm features)
        if profile.dysphagia:
            score += 3
        if profile.odynophagia:
            score += 3

        alarm = len(profile.alarm_symptoms) > 0 or profile.dysphagia or profile.odynophagia

        if score < 6:
            severity = GERDSeverity.NONE
        elif score < 12:
            severity = GERDSeverity.MILD
        elif score < 20:
            severity = GERDSeverity.MODERATE
        else:
            severity = GERDSeverity.SEVERE

        endoscopy = alarm or (severity == GERDSeverity.SEVERE and profile.duration_years > 5)
        ppi_trial = severity.value in ["mild", "moderate", "severe"] and not alarm

        surgery = (severity == GERDSeverity.SEVERE and profile.ppi_response == "none" and
                   not alarm and profile.duration_years > 2)

        management = []
        if alarm:
            management = ["URGENT endoscopy for alarm symptoms", "Rule out malignancy, stricture, Barrett's"]
        elif severity == GERDSeverity.MILD:
            management = ["Lifestyle: elevate head of bed, avoid late meals, weight loss", "Antacids or H2 blocker PRN"]
        elif severity == GERDSeverity.MODERATE:
            management = ["PPI 4-8 week trial (omeprazole 20mg daily before breakfast)", "Lifestyle modifications"]
        elif severity == GERDSeverity.SEVERE:
            management = ["PPI standard dose BID 8-12 weeks", "Maintenance PPI if recurrent", "Endoscopy if refractory"]

        if surgery:
            management.append("Refractory GERD — consider Nissen fundoplication or LINX")
        if profile.chronic_cough:
            management.append("PPI trial for 8-12 weeks before labeling as non-GERD cough")

        follow_up = "Reassess in 4-8 weeks" if ppi_trial else "Endoscopy scheduling" if endoscopy else "As needed"

        return GERDResult(
            score=score,
            severity=severity,
            alarm_symptoms_present=alarm,
            endoscopy_recommended=endoscopy,
            ppi_trial_recommended=ppi_trial,
            surgery_candidate=surgery,
            management=management,
            follow_up=follow_up
        )


def run():
    calc = GERDCalculator()

    print("=" * 60)
    print("GERD Assessment Calculator")
    print("=" * 60)

    profile = GERDProfile(
        heartburn_frequency_per_week=5, heartburn_severity=7,
        regurgitation_frequency_per_week=3, chest_pain=True,
        chronic_cough=True, ppi_response="partial", duration_years=3
    )

    result = calc.calculate(profile)
    print(f"\nScore: {result.score}")
    print(f"Severity: {result.severity.value}")
    print(f"Alarm: {result.alarm_symptoms_present}")
    print(f"Endoscopy: {result.endoscopy_recommended}")
    print(f"PPI trial: {result.ppi_trial_recommended}")
    print(f"Surgery candidate: {result.surgery_candidate}")
    print(f"Management: {result.management}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
