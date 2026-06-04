"""Skill Assessor — rubrics, competency mapping, gap analysis, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class SkillAssessor:
    rubrics: Dict[str, List[str]] = field(default_factory=dict)
    scores: Dict[str, float] = field(default_factory=dict)
    targets: Dict[str, float] = field(default_factory=dict)

    def add_rubric(self, skill: str, levels: List[str]):
        self.rubrics[skill] = levels

    def score(self, skill: str, value: float):
        self.scores[skill] = value

    def gap(self, skill: str) -> float:
        return self.targets.get(skill, 0) - self.scores.get(skill, 0)

    def competency_level(self, skill: str) -> str:
        score = self.scores.get(skill, 0)
        levels = self.rubrics.get(skill, ["beginner", "intermediate", "advanced"])
        idx = min(int(score * len(levels) / 100), len(levels) - 1)
        return levels[idx]

    def gaps(self) -> Dict[str, float]:
        return {s: self.gap(s) for s in self.scores}

    def overall(self) -> float:
        if not self.scores:
            return 0.0
        return sum(self.scores.values()) / len(self.scores)

    def stats(self) -> Dict:
        return {"skills": len(self.scores), "overall": round(self.overall(), 2), "gaps": self.gaps()}

def run():
    sa = SkillAssessor(targets={"python": 80, "math": 70})
    sa.add_rubric("python", ["beginner", "intermediate", "advanced", "expert"])
    sa.score("python", 65)
    sa.score("math", 75)
    print(sa.stats())
    print("Python level:", sa.competency_level("python"))

if __name__ == "__main__":
    run()
