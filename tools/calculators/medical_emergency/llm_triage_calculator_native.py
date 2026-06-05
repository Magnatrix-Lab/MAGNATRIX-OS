"""
Emergency Triage Calculator — Emergency Medicine
Vital signs + presentation scoring for 5-level acuity stratification.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class TriageLevel(Enum):
    RESUSCITATION = 1   # Immediate
    EMERGENT = 2        # < 15 min
    URGENT = 3          # < 30 min
    LESS_URGENT = 4     # < 60 min
    NON_URGENT = 5      # < 120 min


class AgeGroup(Enum):
    INFANT = "infant"
    CHILD = "child"
    ADULT = "adult"
    ELDERLY = "elderly"


@dataclass
class TriageProfile:
    age_group: AgeGroup
    heart_rate: float
    systolic_bp: float
    diastolic_bp: float
    respiratory_rate: float
    oxygen_saturation: float
    temperature_celsius: float
    gcs_score: int = 15
    chief_complaint: str = ""
    pain_score: int = 0  # 0-10
    known_allergies: List[str] = None

    def __post_init__(self):
        if self.known_allergies is None:
            self.known_allergies = []


@dataclass
class TriageResult:
    level: TriageLevel
    level_name: str
    max_wait_minutes: int
    priority: str
    disposition: str
    monitoring: List[str]
    red_flags: List[str]


class TriageCalculator:
    """ESI-inspired 5-level triage calculator."""

    def calculate(self, profile: TriageProfile) -> TriageResult:
        red_flags = []
        score = 0

        # Airway / Breathing red flags
        if profile.oxygen_saturation < 90:
            red_flags.append("Critical hypoxia")
            score += 5
        elif profile.oxygen_saturation < 94:
            score += 2
            red_flags.append("Hypoxia")

        if profile.respiratory_rate < 8 or profile.respiratory_rate > 30:
            red_flags.append("Critical respiratory rate")
            score += 5
        elif profile.respiratory_rate > 24:
            score += 2

        # Circulation red flags
        if profile.systolic_bp < 90:
            red_flags.append("Hypotension")
            score += 5
        elif profile.systolic_bp < 100:
            score += 2

        if profile.heart_rate < 40 or profile.heart_rate > 150:
            red_flags.append("Critical heart rate")
            score += 5
        elif profile.heart_rate > 120 or profile.heart_rate < 50:
            score += 2

        # Neuro / GCS
        if profile.gcs_score <= 8:
            red_flags.append("GCS ≤ 8")
            score += 5
        elif profile.gcs_score <= 12:
            score += 3
            red_flags.append("Altered mental status")

        # Temperature
        if profile.temperature_celsius < 35.0 or profile.temperature_celsius > 40.0:
            red_flags.append("Critical temperature")
            score += 3
        elif profile.temperature_celsius > 38.5 or profile.temperature_celsius < 36.0:
            score += 1

        # Pain
        if profile.pain_score >= 9:
            score += 2

        # Age modifiers
        if profile.age_group == AgeGroup.INFANT:
            score += 1
        elif profile.age_group == AgeGroup.ELDERLY:
            score += 1

        # Chief complaint keywords (simplified)
        critical_complaints = [
            "chest pain", "stroke", "seizure", "overdose", "trauma", "burn",
            "active bleeding", "anaphylaxis", "suicidal", "unconscious"
        ]
        complaint_lower = profile.chief_complaint.lower()
        for kw in critical_complaints:
            if kw in complaint_lower:
                score += 2
                red_flags.append(f"Critical complaint: {kw}")
                break

        # Assign level
        if score >= 5 or len([f for f in red_flags if "Critical" in f or "GCS" in f]) >= 1:
            level = TriageLevel.RESUSCITATION
        elif score >= 3:
            level = TriageLevel.EMERGENT
        elif score >= 1:
            level = TriageLevel.URGENT
        elif profile.pain_score >= 5 or profile.chief_complaint:
            level = TriageLevel.LESS_URGENT
        else:
            level = TriageLevel.NON_URGENT

        level_map = {
            TriageLevel.RESUSCITATION: ("Resuscitation", 0, "Critical", "Trauma bay / Resus room"),
            TriageLevel.EMERGENT: ("Emergent", 15, "High", "ED bed + monitoring"),
            TriageLevel.URGENT: ("Urgent", 30, "Moderate", "ED bed"),
            TriageLevel.LESS_URGENT: ("Less Urgent", 60, "Low", "Waiting area / Fast track"),
            TriageLevel.NON_URGENT: ("Non-Urgent", 120, "Minimal", "Waiting area / Clinic referral"),
        }

        name, wait, priority, disp = level_map[level]

        monitoring = ["Vitals reassessment per protocol"]
        if level.value <= 2:
            monitoring += ["Continuous pulse oximetry", "Cardiac monitoring", "IV access"]
        if level.value <= 3:
            monitoring += ["Repeat BP/HR every 15-30 min"]

        return TriageResult(
            level=level,
            level_name=name,
            max_wait_minutes=wait,
            priority=priority,
            disposition=disp,
            monitoring=monitoring,
            red_flags=red_flags
        )

    def mass_casualty_triage(self, resources_available: int, patients: int) -> str:
        """Simple START/SALT heuristic."""
        ratio = resources_available / patients if patients > 0 else 1.0
        if ratio >= 1.0:
            return "Standard triage — adequate resources"
        elif ratio >= 0.5:
            return "Modified triage — expect delays, prioritize salvageable"
        else:
            return "Disaster triage — START protocol: focus on RPM (Respiration, Perfusion, Mental status)"


def run():
    calc = TriageCalculator()

    print("=" * 60)
    print("Emergency Triage Calculator")
    print("=" * 60)

    cases = [
        TriageProfile(AgeGroup.ADULT, 120, 85, 55, 24, 88, 38.5, 15, "Chest pain", 8),
        TriageProfile(AgeGroup.ELDERLY, 45, 70, 40, 28, 82, 36.0, 8, "Unconscious", 0),
        TriageProfile(AgeGroup.ADULT, 75, 130, 80, 18, 98, 37.2, 15, "Sprained ankle", 3),
    ]

    for i, c in enumerate(cases, 1):
        result = calc.calculate(c)
        print(f"\nCase {i}: {c.chief_complaint}")
        print(f"  Level: {result.level_name} (ESI-{result.level.value})")
        print(f"  Wait: {result.max_wait_minutes} min | Priority: {result.priority}")
        print(f"  Disposition: {result.disposition}")
        print(f"  Red flags: {result.red_flags}")
        print(f"  Monitoring: {result.monitoring}")

    print(f"\nMass casualty: {calc.mass_casualty_triage(5, 12)}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
