"""Talent Matcher — skills, culture fit, gap, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

@dataclass
class TalentMatcher:
    candidate_skills: Set[str] = field(default_factory=set)
    required_skills: Set[str] = field(default_factory=set)
    culture_traits: Set[str] = field(default_factory=set)
    company_culture: Set[str] = field(default_factory=set)

    def skill_match(self) -> float:
        if not self.required_skills:
            return 1.0
        matched = len(self.candidate_skills & self.required_skills)
        return matched / len(self.required_skills)

    def culture_fit(self) -> float:
        if not self.company_culture:
            return 1.0
        matched = len(self.culture_traits & self.company_culture)
        return matched / len(self.company_culture)

    def overall_score(self, skill_weight: float = 0.7) -> float:
        return self.skill_match() * skill_weight + self.culture_fit() * (1 - skill_weight)

    def skill_gaps(self) -> Set[str]:
        return self.required_skills - self.candidate_skills

    def recommendation(self, threshold: float = 0.7) -> str:
        s = self.overall_score()
        if s >= 0.9: return "strong_hire"
        elif s >= threshold: return "hire"
        elif s >= 0.5: return "interview"
        return "pass"

    def stats(self) -> Dict:
        return {
            "skill_match": round(self.skill_match(), 3),
            "culture_fit": round(self.culture_fit(), 3),
            "overall": round(self.overall_score(), 3),
            "gaps": list(self.skill_gaps())
        }

def run():
    tm = TalentMatcher(
        candidate_skills={"python", "sql", "aws"},
        required_skills={"python", "sql", "aws", "docker"},
        culture_traits={"collaborative", "innovative"},
        company_culture={"collaborative", "innovative", "agile"}
    )
    print(tm.stats())
    print("Recommendation:", tm.recommendation())

if __name__ == "__main__":
    run()
