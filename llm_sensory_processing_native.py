"""Native stdlib module: Sensory Processing Calculator
Assesses sensory processing patterns and modulation scores.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class SensoryDomain(Enum):
    AUDITORY = "auditory"
    VISUAL = "visual"
    TACTILE = "tactile"
    VESTIBULAR = "vestibular"
    PROPRIOCEPTIVE = "proprioceptive"
    ORAL = "oral"

class ResponsePattern(Enum):
    LOW_REGISTRATION = "low_registration"
    SEEKING = "seeking"
    SENSITIVITY = "sensitivity"
    AVOIDING = "avoiding"

@dataclass
class SensoryScore:
    domain: SensoryDomain
    score: float
    max_score: float = 75.0

@dataclass
class SensoryProcessingCalculator:
    patient_name: str
    age_years: int
    scores: List[SensoryScore] = field(default_factory=list)

    def total_score(self) -> float:
        return sum(s.score for s in self.scores)

    def avg_score(self) -> float:
        if not self.scores:
            return 0.0
        return self.total_score() / len(self.scores)

    def percentile(self, score: float) -> float:
        if score < 30:
            return 15
        elif score < 40:
            return 30
        elif score < 60:
            return 50
        elif score < 70:
            return 70
        return 85

    def dominant_domain(self) -> str:
        if not self.scores:
            return ""
        highest = max(self.scores, key=lambda s: s.score)
        return highest.domain.value

    def modulation_difficulty(self) -> bool:
        return any(s.score > 60 or s.score < 30 for s in self.scores)

    def by_domain(self) -> Dict[str, float]:
        return {s.domain.value: round(s.score, 1) for s in self.scores}

    def stats(self) -> Dict:
        return {
            "patient": self.patient_name,
            "age": self.age_years,
            "domains": len(self.scores),
            "avg_score": round(self.avg_score(), 1),
            "dominant_domain": self.dominant_domain(),
            "modulation_difficulty": self.modulation_difficulty(),
            "by_domain": self.by_domain(),
        }

def run():
    spc = SensoryProcessingCalculator(
        patient_name="Child-B",
        age_years=7,
        scores=[
            SensoryScore(SensoryDomain.AUDITORY, 65),
            SensoryScore(SensoryDomain.VISUAL, 45),
            SensoryScore(SensoryDomain.TACTILE, 72),
            SensoryScore(SensoryDomain.VESTIBULAR, 55),
            SensoryScore(SensoryDomain.PROPRIIOCEPTIVE, 38),
            SensoryScore(SensoryDomain.ORAL, 68),
        ]
    )
    print(spc.stats())

if __name__ == "__main__":
    run()
