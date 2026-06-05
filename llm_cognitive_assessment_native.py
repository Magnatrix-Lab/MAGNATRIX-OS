"""Native stdlib module: Cognitive Assessment Calculator
Scores cognitive function across memory, attention, and executive domains.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class CognitiveDomain:
    domain: str
    raw_score: float
    max_score: float
    age_scaled_score: float

@dataclass
class CognitiveAssessmentCalculator:
    patient_name: str
    age: int
    education_years: int
    domains: List[CognitiveDomain] = field(default_factory=list)

    def composite_score(self) -> float:
        if not self.domains:
            return 0.0
        return sum(d.age_scaled_score for d in self.domains) / len(self.domains)

    def percentile_rank(self) -> float:
        comp = self.composite_score()
        if comp < 70:
            return 2
        elif comp < 85:
            return 16
        elif comp < 100:
            return 50
        elif comp < 115:
            return 84
        elif comp < 130:
            return 98
        return 99.9

    def cognitive_status(self) -> str:
        comp = self.composite_score()
        if comp < 70:
            return "significant_impairment"
        elif comp < 85:
            return "mild_impairment"
        elif comp < 100:
            return "low_average"
        elif comp < 115:
            return "average"
        elif comp < 130:
            return "high_average"
        return "superior"

    def education_adjusted_score(self) -> float:
        adj = (self.education_years - 12) * 2
        return self.composite_score() + adj

    def domain_strengths(self) -> List[str]:
        sorted_domains = sorted(self.domains, key=lambda d: d.age_scaled_score, reverse=True)
        return [d.domain for d in sorted_domains[:2]]

    def domain_weaknesses(self) -> List[str]:
        sorted_domains = sorted(self.domains, key=lambda d: d.age_scaled_score)
        return [d.domain for d in sorted_domains[:2]]

    def stats(self) -> Dict:
        return {
            "patient": self.patient_name,
            "age": self.age,
            "education_years": self.education_years,
            "composite_score": round(self.composite_score(), 1),
            "percentile": self.percentile_rank(),
            "status": self.cognitive_status(),
            "education_adjusted": round(self.education_adjusted_score(), 1),
            "strengths": self.domain_strengths(),
            "weaknesses": self.domain_weaknesses(),
        }

def run():
    cac = CognitiveAssessmentCalculator(
        patient_name="Patient-Y",
        age=68,
        education_years=16,
        domains=[
            CognitiveDomain("memory", 18, 30, 85),
            CognitiveDomain("attention", 22, 30, 95),
            CognitiveDomain("executive", 15, 30, 78),
            CognitiveDomain("language", 25, 30, 105),
            CognitiveDomain("visuospatial", 20, 30, 88),
        ]
    )
    print(cac.stats())

if __name__ == "__main__":
    run()
