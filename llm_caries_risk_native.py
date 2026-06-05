"""Native stdlib module: Caries Risk Calculator
Assesses dental caries risk by diet, hygiene, and medical factors.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class RiskLevel(Enum):
    LOW = 1
    MODERATE = 2
    HIGH = 3
    EXTREME = 4

@dataclass
class CariesRiskCalculator:
    patient_name: str
    age: int
    sugar_exposures_per_day: int
    brushing_frequency_per_day: int
    fluoride_exposure: bool = True
    dry_mouth: bool = False
    previous_caries: bool = False
    orthodontic_appliance: bool = False

    def diet_score(self) -> int:
        if self.sugar_exposures_per_day <= 2:
            return 1
        elif self.sugar_exposures_per_day <= 4:
            return 2
        elif self.sugar_exposures_per_day <= 6:
            return 3
        return 4

    def hygiene_score(self) -> int:
        if self.brushing_frequency_per_day >= 2:
            return 1
        elif self.brushing_frequency_per_day == 1:
            return 2
        return 4

    def risk_score(self) -> int:
        score = self.diet_score() + self.hygiene_score()
        if not self.fluoride_exposure:
            score += 2
        if self.dry_mouth:
            score += 2
        if self.previous_caries:
            score += 2
        if self.orthodontic_appliance:
            score += 1
        if self.age < 6 or self.age > 65:
            score += 1
        return min(12, score)

    def risk_level(self) -> RiskLevel:
        s = self.risk_score()
        if s <= 3:
            return RiskLevel.LOW
        elif s <= 5:
            return RiskLevel.MODERATE
        elif s <= 8:
            return RiskLevel.HIGH
        return RiskLevel.EXTREME

    def recall_interval_months(self) -> int:
        level = self.risk_level()
        if level == RiskLevel.LOW:
            return 12
        elif level == RiskLevel.MODERATE:
            return 6
        elif level == RiskLevel.HIGH:
            return 3
        return 1

    def stats(self) -> Dict:
        return {
            "patient": self.patient_name,
            "age": self.age,
            "risk_score": self.risk_score(),
            "risk_level": self.risk_level().name,
            "recall_months": self.recall_interval_months(),
            "diet_score": self.diet_score(),
            "hygiene_score": self.hygiene_score(),
        }

def run():
    crc = CariesRiskCalculator(patient_name="Alice", age=25, sugar_exposures_per_day=3, brushing_frequency_per_day=2, fluoride_exposure=True, previous_caries=True)
    print(crc.stats())

if __name__ == "__main__":
    run()
