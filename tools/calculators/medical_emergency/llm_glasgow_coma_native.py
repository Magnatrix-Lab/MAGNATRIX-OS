"""
Glasgow Coma Scale (GCS) Calculator — Emergency Medicine
Eye / Verbal / Motor scoring, total GCS, and prognostic guidance.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class EyeResponse(Enum):
    SPONTANEOUS = 4
    TO_SPEECH = 3
    TO_PAIN = 2
    NONE = 1


class VerbalResponse(Enum):
    ORIENTED = 5
    CONFUSED = 4
    INAPPROPRIATE_WORDS = 3
    INCOMPREHENSIBLE_SOUNDS = 2
    NONE = 1


class MotorResponse(Enum):
    OBEYS_COMMANDS = 6
    LOCALIZES_PAIN = 5
    WITHDRAWS_FROM_PAIN = 4
    FLEXION_DECORTICATE = 3
    EXTENSION_DECEREBRATE = 2
    NONE = 1


@dataclass
class GCSProfile:
    eye: EyeResponse
    verbal: VerbalResponse
    motor: MotorResponse
    intubated: bool = False
    age_years: int = 35
    pupil_reactive: bool = True
    pupil_size_mm: float = 3.0


@dataclass
class GCSResult:
    total_score: int
    eye_score: int
    verbal_score: int
    motor_score: int
    severity: str
    prognosis: str
    airway_risk: bool
    monitoring: List[str]
    notes: List[str]


class GlasgowComaCalculator:
    """GCS scoring with severity and prognostic guidance."""

    def calculate(self, profile: GCSProfile) -> GCSResult:
        eye = profile.eye.value
        verbal = 0 if profile.intubated else profile.verbal.value
        motor = profile.motor.value
        total = eye + verbal + motor

        if total <= 8:
            severity = "Severe (Coma)"
            prognosis = "Poor — high mortality. Protect airway. CT head ASAP."
        elif total <= 12:
            severity = "Moderate (Altered)"
            prognosis = "Guarded — close monitoring, rule out intracranial pathology."
        elif total <= 14:
            severity = "Mild (Minor impairment)"
            prognosis = "Favorable — monitor for deterioration."
        else:
            severity = "Normal"
            prognosis = "Excellent"

        airway_risk = total <= 8 or profile.intubated

        monitoring = ["Neuro checks every 15-30 min"]
        if airway_risk:
            monitoring += ["Airway protection", "Intubation readiness", "ETCO2 monitoring"]
        if total <= 12:
            monitoring += ["CT head", "ICU admission", "ICP monitoring if indicated"]
        if not profile.pupil_reactive:
            monitoring += ["Emergent neurosurgical consult"]

        notes = []
        if profile.intubated:
            notes.append("Verbal score = 0 (T) — intubated. Document as E{}V{}M{}T = {}T".format(
                eye, profile.verbal.value, motor, total))
        else:
            notes.append(f"E{eye}V{verbal}M{motor} = {total}")
        if not profile.pupil_reactive:
            notes.append("Non-reactive pupil — poor prognostic sign.")
        if profile.pupil_size_mm < 2 or profile.pupil_size_mm > 6:
            notes.append("Abnormal pupil size — potential herniation/structural lesion.")

        return GCSResult(
            total_score=total,
            eye_score=eye,
            verbal_score=verbal,
            motor_score=motor,
            severity=severity,
            prognosis=prognosis,
            airway_risk=airway_risk,
            monitoring=monitoring,
            notes=notes
        )

    def pediatric_verbal(self, age_months: int) -> dict:
        """Age-appropriate pediatric verbal response."""
        if age_months < 6:
            return {"scale": "Modified", "max": 2, "description": "Cries/moans vs silent"}
        elif age_months < 24:
            return {"scale": "Modified", "max": 3, "description": "Words/crying vs inappropriate vs silent"}
        elif age_months < 60:
            return {"scale": "Modified", "max": 4, "description": "Oriented words vs confused vs crying vs silent"}
        else:
            return {"scale": "Standard", "max": 5, "description": "Standard GCS verbal"}


def run():
    calc = GlasgowComaCalculator()

    print("=" * 60)
    print("Glasgow Coma Scale Calculator")
    print("=" * 60)

    cases = [
        GCSProfile(EyeResponse.SPONTANEOUS, VerbalResponse.ORIENTED, MotorResponse.OBEYS_COMMANDS),
        GCSProfile(EyeResponse.TO_PAIN, VerbalResponse.INCOMPREHENSIBLE_SOUNDS, MotorResponse.FLEXION_DECORTICATE, pupil_reactive=False),
        GCSProfile(EyeResponse.NONE, VerbalResponse.NONE, MotorResponse.NONE, intubated=True),
    ]

    for i, c in enumerate(cases, 1):
        result = calc.calculate(c)
        print(f"\nCase {i}: E{result.eye_score}V{result.verbal_score}M{result.motor_score} = {result.total_score}")
        print(f"  Severity: {result.severity}")
        print(f"  Prognosis: {result.prognosis}")
        print(f"  Airway risk: {result.airway_risk}")
        print(f"  Monitoring: {result.monitoring}")
        print(f"  Notes: {result.notes}")

    print(f"\nPediatric verbal (18 months): {calc.pediatric_verbal(18)}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
