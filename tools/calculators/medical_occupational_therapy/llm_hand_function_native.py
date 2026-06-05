"""Native stdlib module: Hand Function Calculator
Scores hand dexterity, grip strength, and fine motor function.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class DominantHand(Enum):
    RIGHT = "right"
    LEFT = "left"
    AMBIDEXTROUS = "ambidextrous"

@dataclass
class HandFunctionCalculator:
    patient_name: str
    dominant_hand: DominantHand
    right_grip_kg: float
    left_grip_kg: float
    right_pinch_kg: float
    left_pinch_kg: float
    nine_peg_test_sec: float
    age: int
    sex: str

    def grip_asymmetry_pct(self) -> float:
        total = self.right_grip_kg + self.left_grip_kg
        if total == 0:
            return 0.0
        return (abs(self.right_grip_kg - self.left_grip_kg) / ((self.right_grip_kg + self.left_grip_kg) / 2)) * 100

    def dominant_grip_kg(self) -> float:
        if self.dominant_hand == DominantHand.LEFT:
            return self.left_grip_kg
        return self.right_grip_kg

    def grip_normative_pct(self) -> float:
        expected = 45.0 if self.sex.lower() == "male" else 30.0
        if expected == 0:
            return 0.0
        return (self.dominant_grip_kg() / expected) * 100

    def fine_motor_rating(self) -> str:
        if self.nine_peg_test_sec < 15:
            return "excellent"
        elif self.nine_peg_test_sec < 20:
            return "good"
        elif self.nine_peg_test_sec < 25:
            return "fair"
        elif self.nine_peg_test_sec < 30:
            return "poor"
        return "very_poor"

    def dexterity_score(self) -> int:
        score = 0
        if self.grip_normative_pct() > 80:
            score += 4
        elif self.grip_normative_pct() > 50:
            score += 2
        if self.nine_peg_test_sec < 20:
            score += 4
        elif self.nine_peg_test_sec < 25:
            score += 2
        return min(8, score)

    def stats(self) -> Dict:
        return {
            "patient": self.patient_name,
            "dominant_hand": self.dominant_hand.value,
            "dominant_grip_kg": round(self.dominant_grip_kg(), 1),
            "grip_asymmetry_pct": round(self.grip_asymmetry_pct(), 1),
            "grip_normative_pct": round(self.grip_normative_pct(), 1),
            "fine_motor_rating": self.fine_motor_rating(),
            "dexterity_score": self.dexterity_score(),
        }

def run():
    hfc = HandFunctionCalculator(patient_name="John", dominant_hand=DominantHand.RIGHT, right_grip_kg=42, left_grip_kg=38, right_pinch_kg=8, left_pinch_kg=7, nine_peg_test_sec=18, age=35, sex="male")
    print(hfc.stats())

if __name__ == "__main__":
    run()
