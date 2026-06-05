"""Nursing Assessment — ADLs, Braden, fall risk, pain, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class NursingAssessment:
    adl_score: int = 6
    """0-6, 6 is fully independent"""
    mobility: int = 4
    nutrition: int = 4
    friction_shear: int = 3
    sensory_perception: int = 4
    moisture: int = 4
    activity: int = 4

    def braden_score(self) -> int:
        return self.mobility + self.nutrition + self.friction_shear + self.sensory_perception + self.moisture + self.activity

    def braden_risk(self) -> str:
        s = self.braden_score()
        if s <= 9: return "very high"
        elif s <= 12: return "high"
        elif s <= 14: return "moderate"
        elif s <= 18: return "mild"
        return "no risk"

    def fall_risk_morse(self, history: bool, secondary_diagnosis: bool, ambulatory: str, iv: bool, gait: str, mental_status: str) -> int:
        score = 0
        if history: score += 25
        if secondary_diagnosis: score += 15
        if ambulatory == "furniture": score += 30
        elif ambulatory == "weak": score += 15
        if iv: score += 20
        if gait == "impaired": score += 20
        elif gait == "weak": score += 10
        if mental_status == "forgets": score += 15
        return score

    def fall_risk_level(self, morse_score: int) -> str:
        if morse_score >= 50: return "high"
        elif morse_score >= 25: return "moderate"
        return "low"

    def pain_scale(self, score: int) -> str:
        if score == 0: return "no pain"
        elif score <= 3: return "mild"
        elif score <= 6: return "moderate"
        return "severe"

    def stats(self, pain_score: int = 3, morse_score: int = 30) -> Dict:
        return {
            "braden": self.braden_score(),
            "braden_risk": self.braden_risk(),
            "fall_risk": self.fall_risk_level(morse_score),
            "pain": self.pain_scale(pain_score)
        }

def run():
    na = NursingAssessment(mobility=3, nutrition=3, friction_shear=2, sensory_perception=3, moisture=2, activity=2)
    print(na.stats(pain_score=5, morse_score=55))
    print("Morse calculation:", na.fall_risk_morse(True, True, "furniture", True, "impaired", "forgets"))

if __name__ == "__main__":
    run()
